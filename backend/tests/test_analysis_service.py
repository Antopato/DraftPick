"""Service-level tests: token/game resolution, caching, degradation.

Real in-memory SQLite (shared pool) + fake data sources, no network.
"""

import asyncio

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base
from app.models import DraftAction, Game, Room
from app.services import analysis_service
from app.services.lanes import ChampionMeta
from app.services.ugg import MatchupData

BLUE = ["BTop", "BJg", "BMid", "BBot", "BSup"]
RED = ["RTop", "RJg", "RMid", "RBot", "RSup"]
LANES = ["top", "jungle", "mid", "bot", "support"]


@pytest.fixture
def db_session_factory():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


@pytest.fixture
def room(db_session_factory):
    session = db_session_factory()
    room = Room(mode="standard", best_of=1)
    session.add(room)
    session.flush()
    game = Game(room_id=room.id, game_number=1, status="completed")
    session.add(game)
    session.flush()
    turn = 0
    for team, picks in (("blue", BLUE), ("red", RED)):
        for pick, lane in zip(picks, LANES):
            session.add(
                DraftAction(
                    game_id=game.id,
                    turn_index=turn,
                    action_type="pick",
                    team=team,
                    champion_id=pick,
                    lane=lane,
                )
            )
            turn += 1
    session.commit()
    info = {
        "blue_token": room.blue_token,
        "spectator_token": room.spectator_token,
        "game_id": game.id,
    }
    session.close()
    return info


@pytest.fixture
def wired(monkeypatch, db_session_factory):
    """Point the service at the test DB and fake every external source."""
    monkeypatch.setattr(analysis_service, "get_session", db_session_factory)

    async def fake_version():
        return "16.15.1"

    async def fake_numeric_ids():
        return {cid: 100 + i for i, cid in enumerate(BLUE + RED)}

    async def fake_tags():
        return {cid: ["Fighter"] for cid in BLUE + RED}

    async def fake_meta():
        return (
            {
                cid: ChampionMeta(
                    lanes=[lane],
                    attack_type="MELEE",
                    attack_range=175,
                    damage_type="PHYSICAL_DAMAGE",
                    ratings={"damage": 2, "toughness": 2, "control": 1, "mobility": 1, "utility": 1},
                )
                for team in (BLUE, RED)
                for cid, lane in zip(team, LANES)
            },
            False,
        )

    async def fake_items():
        return [], False

    monkeypatch.setattr(analysis_service.catalog, "get_version", fake_version)
    monkeypatch.setattr(analysis_service.catalog, "get_numeric_ids", fake_numeric_ids)
    monkeypatch.setattr(analysis_service.catalog, "get_tags", fake_tags)
    monkeypatch.setattr(analysis_service.lane_catalog, "get_meta", fake_meta)
    monkeypatch.setattr(analysis_service.item_catalog, "get_legendary_items", fake_items)
    monkeypatch.setattr(
        analysis_service.snapshot_store,
        "get",
        lambda patch: MatchupData(patch="16_15", stale=False, champions={}),
    )


def run(coro):
    return asyncio.run(coro)


class TestService:
    def test_unknown_token_404(self, wired):
        with pytest.raises(analysis_service.AnalysisError) as err:
            run(analysis_service.get_or_compute_analysis("nope", None))
        assert err.value.status_code == 404

    def test_not_completed_409(self, wired, db_session_factory, room):
        session = db_session_factory()
        session.query(Game).filter(Game.id == room["game_id"]).update(
            {"status": "in_progress"}
        )
        session.commit()
        session.close()
        with pytest.raises(analysis_service.AnalysisError) as err:
            run(analysis_service.get_or_compute_analysis(room["blue_token"], None))
        assert err.value.status_code == 409

    def test_compute_then_cache_hit(self, wired, room):
        first = run(analysis_service.get_or_compute_analysis(room["blue_token"], None))
        assert first["cached"] is False
        assert first["game_number"] == 1
        second = run(
            analysis_service.get_or_compute_analysis(room["spectator_token"], 1)
        )
        assert second["cached"] is True
        assert second["verdict"] == first["verdict"]

    def test_lane_change_recomputes(self, wired, db_session_factory, room):
        first = run(analysis_service.get_or_compute_analysis(room["blue_token"], None))
        assert first["cached"] is False
        session = db_session_factory()
        session.query(DraftAction).filter(
            DraftAction.game_id == room["game_id"],
            DraftAction.champion_id == "BTop",
        ).update({"lane": None})
        session.commit()
        session.close()
        again = run(analysis_service.get_or_compute_analysis(room["blue_token"], None))
        assert again["cached"] is False
        assert again["lanes_inferred"] is True

    def test_missing_game_404(self, wired, room):
        with pytest.raises(analysis_service.AnalysisError) as err:
            run(analysis_service.get_or_compute_analysis(room["blue_token"], 3))
        assert err.value.status_code == 404
