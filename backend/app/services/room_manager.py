"""Live rooms: in-memory engines, WebSocket connections, authoritative timers.

All mutations of a room happen under its asyncio lock. After every
state-changing event the FULL state is broadcast to every connection
(never diffs), so a reconnect only needs one `state` message.

State is always rebuildable from the DB (DraftAction rows), so a server
restart (e.g. Render free tier) loses at most the pending ready-check flags.
"""

import asyncio
import time
from datetime import datetime, timezone
from typing import Any, Literal

from fastapi import WebSocket

from ..db import get_session
from ..draft.engine import (
    DraftEngine,
    DraftError,
    DraftStatus,
    InvalidActionError,
    TurnResult,
)
from ..draft.sequence import ActionType, Team, slot_number
from ..models import DraftAction, Game, Room
from .ddragon import catalog

Role = Literal["blue", "red", "spectator"]


class UnknownTokenError(Exception):
    pass


def _now_ms() -> int:
    return int(time.time() * 1000)


class LiveRoom:
    def __init__(self, room: Room, game: Game, engine: DraftEngine, prior_picks: set[str]) -> None:
        self.room_id = room.id
        self.mode = room.mode
        self.best_of = room.best_of
        self.timer_seconds = room.timer_seconds
        self.blue_name = room.blue_name
        self.red_name = room.red_name
        self.tokens: dict[str, Role] = {
            room.blue_token: "blue",
            room.red_token: "red",
            room.spectator_token: "spectator",
        }
        self.game_id = game.id
        self.game_number = game.game_number
        self.engine = engine
        self.prior_picks = prior_picks  # picks from earlier games in the series
        self.connections: dict[WebSocket, Role] = {}
        self.deadline_ms: int | None = None
        self.timer_task: asyncio.Task | None = None
        self.lock = asyncio.Lock()

    # --- state serialization --------------------------------------------

    def status_label(self) -> str:
        if self.engine.status == DraftStatus.COMPLETED:
            is_last = self.game_number >= self.best_of
            return "series_completed" if is_last else "completed"
        return self.engine.status.value

    def state_dict(self) -> dict[str, Any]:
        engine = self.engine
        current = engine.current_turn
        return {
            "room": {
                "mode": self.mode,
                "best_of": self.best_of,
                "timer_seconds": self.timer_seconds,
                "blue_name": self.blue_name,
                "red_name": self.red_name,
            },
            "game_number": self.game_number,
            "status": self.status_label(),
            "ready": {
                "blue": engine.ready[Team.BLUE],
                "red": engine.ready[Team.RED],
            },
            "connected": {
                "blue": any(r == "blue" for r in self.connections.values()),
                "red": any(r == "red" for r in self.connections.values()),
            },
            "turn_index": (
                engine.turn_index
                if engine.status == DraftStatus.IN_PROGRESS
                else None
            ),
            "current_turn": (
                {
                    "team": current[0].value,
                    "action_type": current[1].value,
                    "slot": slot_number(engine.turn_index),
                }
                if current
                else None
            ),
            "deadline": self.deadline_ms,
            "server_now": _now_ms(),
            "bans": {
                "blue": engine.bans[Team.BLUE],
                "red": engine.bans[Team.RED],
            },
            "picks": {
                "blue": engine.picks[Team.BLUE],
                "red": engine.picks[Team.RED],
            },
            "hovered": engine.hovered,
            "fearless_blocked": sorted(engine.fearless_blocked),
        }


class RoomManager:
    def __init__(self) -> None:
        self._rooms: dict[str, LiveRoom] = {}
        self._load_lock = asyncio.Lock()

    # --- loading ---------------------------------------------------------

    async def get_by_token(self, token: str) -> tuple[LiveRoom, Role]:
        async with self._load_lock:
            for live in self._rooms.values():
                if token in live.tokens:
                    return live, live.tokens[token]
            live = await self._load_from_db(token)
            self._rooms[live.room_id] = live
            return live, live.tokens[token]

    async def _load_from_db(self, token: str) -> LiveRoom:
        pool = await catalog.get_pool()
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
                raise UnknownTokenError()

            games = room.games
            game = games[-1]

            prior_picks: set[str] = set()
            if room.mode == "fearless":
                for g in games[:-1]:
                    prior_picks.update(
                        a.champion_id
                        for a in g.actions
                        if a.action_type == "pick" and a.champion_id
                    )

            engine = DraftEngine(
                champion_pool=pool,
                fearless_blocked=prior_picks if room.mode == "fearless" else set(),
            )
            if game.status != "waiting":
                engine.replay(
                    [
                        TurnResult(
                            turn_index=a.turn_index,
                            team=Team(a.team),
                            action_type=ActionType(a.action_type),
                            champion_id=a.champion_id,
                            is_auto=a.is_auto,
                        )
                        for a in game.actions
                    ]
                )
            return LiveRoom(room, game, engine, prior_picks)
        finally:
            session.close()

    # --- connections -----------------------------------------------------

    async def register(self, live: LiveRoom, ws: WebSocket, role: Role) -> None:
        async with live.lock:
            live.connections[ws] = role
        await self.broadcast(live)

    async def unregister(self, live: LiveRoom, ws: WebSocket) -> None:
        async with live.lock:
            live.connections.pop(ws, None)
        await self.broadcast(live)

    # --- message handling ------------------------------------------------

    async def handle(self, live: LiveRoom, team: Team, message: dict[str, Any]) -> None:
        """Handle a captain message. Raises DraftError on rule violations."""
        msg_type = message.get("type")
        async with live.lock:
            if msg_type == "ready":
                started = live.engine.set_ready(team)
                if started:
                    self._mark_game_in_progress(live)
                    self._schedule_timer(live)
            elif msg_type == "hover":
                live.engine.hover(team, message.get("champion_id"))
            elif msg_type == "confirm":
                champion_id = message.get("champion_id")
                if not isinstance(champion_id, str):
                    raise InvalidActionError("Debes elegir un campeón.")
                result = live.engine.confirm(team, champion_id)
                self._after_action(live, result)
            elif msg_type == "next_game":
                await self._next_game(live)
            else:
                raise InvalidActionError("Acción desconocida.")
        await self.broadcast(live)

    # --- timer -----------------------------------------------------------

    def _schedule_timer(self, live: LiveRoom) -> None:
        self._cancel_timer(live)
        live.deadline_ms = _now_ms() + live.timer_seconds * 1000
        live.timer_task = asyncio.create_task(
            self._timer_fire(live, live.deadline_ms, live.engine.turn_index)
        )

    def _cancel_timer(self, live: LiveRoom) -> None:
        if live.timer_task is not None:
            live.timer_task.cancel()
            live.timer_task = None
        live.deadline_ms = None

    async def _timer_fire(self, live: LiveRoom, deadline_ms: int, turn_index: int) -> None:
        await asyncio.sleep(max(0, deadline_ms - _now_ms()) / 1000)
        async with live.lock:
            # The turn may have been resolved while we were waiting.
            if (
                live.engine.status != DraftStatus.IN_PROGRESS
                or live.engine.turn_index != turn_index
                or live.deadline_ms != deadline_ms
            ):
                return
            result = live.engine.resolve_timeout()
            self._after_action(live, result)
        await self.broadcast(live)

    # --- persistence & turn flow ----------------------------------------

    def _mark_game_in_progress(self, live: LiveRoom) -> None:
        session = get_session()
        try:
            game = session.get(Game, live.game_id)
            game.status = "in_progress"
            session.commit()
        finally:
            session.close()

    def _after_action(self, live: LiveRoom, result: TurnResult) -> None:
        """Persist a confirmed action and advance timer / complete the game."""
        session = get_session()
        try:
            session.add(
                DraftAction(
                    game_id=live.game_id,
                    turn_index=result.turn_index,
                    action_type=result.action_type.value,
                    team=result.team.value,
                    champion_id=result.champion_id,
                    is_auto=result.is_auto,
                )
            )
            if live.engine.status == DraftStatus.COMPLETED:
                game = session.get(Game, live.game_id)
                game.status = "completed"
                game.completed_at = datetime.now(timezone.utc)
            session.commit()
        finally:
            session.close()

        if live.engine.status == DraftStatus.IN_PROGRESS:
            self._schedule_timer(live)
        else:
            self._cancel_timer(live)

    async def _next_game(self, live: LiveRoom) -> None:
        if live.engine.status != DraftStatus.COMPLETED:
            raise InvalidActionError("El draft actual aún no ha terminado.")
        if live.game_number >= live.best_of:
            raise InvalidActionError("La serie ya ha terminado.")

        if live.mode == "fearless":
            for picks in live.engine.picks.values():
                live.prior_picks.update(picks)

        pool = await catalog.get_pool()
        session = get_session()
        try:
            game = Game(room_id=live.room_id, game_number=live.game_number + 1)
            session.add(game)
            session.commit()
            live.game_id = game.id
            live.game_number = game.game_number
        finally:
            session.close()

        live.engine = DraftEngine(
            champion_pool=pool,
            fearless_blocked=set(live.prior_picks) if live.mode == "fearless" else set(),
        )
        self._cancel_timer(live)

    # --- broadcast -------------------------------------------------------

    async def broadcast(self, live: LiveRoom) -> None:
        async with live.lock:
            base = live.state_dict()
            targets = list(live.connections.items())
        dead: list[WebSocket] = []
        for ws, role in targets:
            try:
                await ws.send_json({"type": "state", "state": {**base, "your_role": role}})
            except Exception:
                dead.append(ws)
        if dead:
            async with live.lock:
                for ws in dead:
                    live.connections.pop(ws, None)


manager = RoomManager()
