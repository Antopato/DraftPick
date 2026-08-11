"""IO orchestrator for the post-draft analysis.

Resolves the room by token (spectators included — the endpoint is read-only),
gathers every data source with per-source degradation, calls the pure
analysis engine, and caches the result per (game, lanes fingerprint) so lane
reassignments recompute and everything else is served from the DB.
"""

import asyncio
import hashlib
import json
from datetime import datetime, timezone

from ..analysis.engine import analyze
from ..analysis.types import AnalysisInput, ChampionProfile, TeamInput
from ..db import get_session
from ..models import Game, GameAnalysis, Room
from .ddragon import catalog, to_ugg_patch
from .items import item_catalog
from .lanes import lane_catalog
from .ugg import snapshot_store

_overrides_cache: dict | None = None


class AnalysisError(Exception):
    """Domain error with a user-facing es-ES message and an HTTP status."""

    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def _load_game(token: str, game_number: int | None) -> tuple[dict, dict]:
    """Returns (teams, meta) read in one short-lived session."""
    session = get_session()
    try:
        room = (
            session.query(Room)
            .filter(
                (Room.blue_token == token)
                | (Room.red_token == token)
                | (Room.spectator_token == token)
            )
            .first()
        )
        if room is None:
            raise AnalysisError(404, "Sala no encontrada.")
        games = room.games
        if game_number is None:
            completed = [g for g in games if g.status == "completed"]
            if not completed:
                raise AnalysisError(409, "El draft aún no ha terminado.")
            game = completed[-1]
        else:
            game = next((g for g in games if g.game_number == game_number), None)
            if game is None:
                raise AnalysisError(404, "Partida no encontrada.")
            if game.status != "completed":
                raise AnalysisError(409, "El draft aún no ha terminado.")

        teams: dict[str, list[tuple[str, str | None]]] = {"blue": [], "red": []}
        for action in game.actions:  # ordered by turn_index
            if action.action_type == "pick" and action.champion_id:
                teams[action.team].append((action.champion_id, action.lane))
        if len(teams["blue"]) != 5 or len(teams["red"]) != 5:
            raise AnalysisError(409, "El draft aún no ha terminado.")
        return teams, {"game_id": game.id, "game_number": game.game_number}
    finally:
        session.close()


def _fingerprint(teams: dict) -> str:
    canonical = json.dumps(teams, sort_keys=True)
    return hashlib.sha1(canonical.encode()).hexdigest()


def _load_cached_analysis(game_id: str, fingerprint: str) -> dict | None:
    session = get_session()
    try:
        row = (
            session.query(GameAnalysis)
            .filter(
                GameAnalysis.game_id == game_id,
                GameAnalysis.lanes_fingerprint == fingerprint,
            )
            .order_by(GameAnalysis.created_at.desc())
            .first()
        )
        return json.loads(row.payload) if row else None
    except Exception:
        return None
    finally:
        session.close()


def _store_analysis(game_id: str, fingerprint: str, patch: str, payload: dict) -> None:
    session = get_session()
    try:
        session.query(GameAnalysis).filter(GameAnalysis.game_id == game_id).delete()
        session.add(
            GameAnalysis(
                game_id=game_id,
                lanes_fingerprint=fingerprint,
                patch=patch,
                payload=json.dumps(payload, separators=(",", ":")),
            )
        )
        session.commit()
    except Exception:
        session.rollback()
    finally:
        session.close()


def _phase_overrides() -> dict:
    global _overrides_cache
    if _overrides_cache is None:
        from ..analysis.spikes import load_overrides

        _overrides_cache = load_overrides()
    return _overrides_cache


async def get_or_compute_analysis(token: str, game_number: int | None) -> dict:
    teams, meta = await asyncio.to_thread(_load_game, token, game_number)
    fingerprint = _fingerprint(teams)

    cached = await asyncio.to_thread(_load_cached_analysis, meta["game_id"], fingerprint)
    # A partial payload (source down at compute time) is recoverable: skip the
    # cache so it recomputes once the data is back.
    if cached is not None and not cached.get("partial"):
        return {**cached, "game_number": meta["game_number"], "cached": True}

    # Gather sources; each degrades to "no data" instead of failing the call.
    try:
        version = await catalog.get_version()
    except Exception:
        version = ""
    try:
        numeric_ids = await catalog.get_numeric_ids()
        tags = await catalog.get_tags()
    except Exception:
        numeric_ids, tags = {}, {}
    champion_meta, meta_stale = await lane_catalog.get_meta()
    item_costs, _items_stale = await item_catalog.get_legendary_items()

    matchup_data = None
    if version:
        matchup_data = await asyncio.to_thread(
            snapshot_store.get, to_ugg_patch(version)
        )

    profiles = {}
    for cid, _lane in (*teams["blue"], *teams["red"]):
        m = champion_meta.get(cid)
        profiles[cid] = ChampionProfile(
            champion_id=cid,
            numeric_id=numeric_ids.get(cid),
            tags=tuple(tags.get(cid, ())),
            lanes=tuple(m.lanes) if m else (),
            attack_type=m.attack_type if m else None,
            attack_range=m.attack_range if m else None,
            damage_type=m.damage_type if m else None,
            ratings=dict(m.ratings) if m else {},
        )

    result = analyze(
        AnalysisInput(
            blue=TeamInput(
                picks=tuple(c for c, _ in teams["blue"]),
                lanes=tuple(lane for _, lane in teams["blue"]),
            ),
            red=TeamInput(
                picks=tuple(c for c, _ in teams["red"]),
                lanes=tuple(lane for _, lane in teams["red"]),
            ),
            profiles=profiles,
            matchups=matchup_data.champions if matchup_data else None,
            matchups_patch=matchup_data.patch if matchup_data else None,
            matchups_stale=matchup_data.stale if matchup_data else False,
            item_costs=tuple(item_costs),
            profiles_stale=meta_stale,
            phase_overrides=_phase_overrides(),
            patch=version,
        )
    )
    result["computed_at"] = datetime.now(timezone.utc).isoformat()

    if not result["partial"]:
        await asyncio.to_thread(
            _store_analysis, meta["game_id"], fingerprint, version, result
        )
    return {**result, "game_number": meta["game_number"], "cached": False}
