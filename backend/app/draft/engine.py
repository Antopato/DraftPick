"""Pure draft state machine. No IO, no timers, no DB — fully unit-testable.

All validation lives here (server-authoritative): turn ownership, champion
legality, fearless blocks. Error messages are user-facing Spanish (es-ES);
everything else is English.

The turn timer itself lives in RoomManager; when it fires it calls
resolve_timeout() on this engine.
"""

import random
from dataclasses import dataclass
from enum import Enum

from .sequence import DRAFT_SEQUENCE, TOTAL_TURNS, ActionType, Team


class DraftError(Exception):
    """Base for all draft rule violations. str(e) is safe to show to the user."""


class NotYourTurnError(DraftError):
    pass


class ChampionUnavailableError(DraftError):
    pass


class InvalidActionError(DraftError):
    pass


class DraftStatus(str, Enum):
    WAITING = "waiting"  # ready check pending
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


# Lanes a champion can be assigned to once the draft is over.
LANES: frozenset[str] = frozenset({"top", "jungle", "mid", "bot", "support"})


@dataclass(frozen=True)
class TurnResult:
    """A confirmed action, ready to be persisted as a DraftAction row."""

    turn_index: int
    team: Team
    action_type: ActionType
    champion_id: str | None  # None = skipped ban (timeout without hover)
    is_auto: bool
    lane: str | None = None  # post-draft lane for picks; None otherwise


class DraftEngine:
    def __init__(
        self,
        champion_pool: set[str],
        fearless_blocked: set[str] | None = None,
        rng: random.Random | None = None,
    ) -> None:
        if not champion_pool:
            raise ValueError("champion_pool must not be empty")
        self.champion_pool = set(champion_pool)
        self.fearless_blocked = set(fearless_blocked or ())
        self._rng = rng or random.Random()

        self.status = DraftStatus.WAITING
        self.ready: dict[Team, bool] = {Team.BLUE: False, Team.RED: False}
        self.turn_index = 0
        self.bans: dict[Team, list[str | None]] = {Team.BLUE: [], Team.RED: []}
        self.picks: dict[Team, list[str]] = {Team.BLUE: [], Team.RED: []}
        self.hovered: str | None = None
        # Lanes assigned after the draft, parallel to picks[team]. pick_turns
        # maps each pick's list index back to its turn_index (for persistence).
        self.lanes: dict[Team, list[str | None]] = {Team.BLUE: [], Team.RED: []}
        self.pick_turns: dict[Team, list[int]] = {Team.BLUE: [], Team.RED: []}

    # --- queries ---------------------------------------------------------

    @property
    def current_turn(self) -> tuple[Team, ActionType] | None:
        if self.status != DraftStatus.IN_PROGRESS:
            return None
        return DRAFT_SEQUENCE[self.turn_index]

    def unavailable(self) -> set[str]:
        """Champions banned or picked in THIS game."""
        taken = {c for bans in self.bans.values() for c in bans if c is not None}
        taken.update(c for picks in self.picks.values() for c in picks)
        return taken

    def selectable(self) -> set[str]:
        """Champions that can currently be banned or picked.

        Fearless-blocked champions cannot be picked nor banned (banning one
        would waste the ban, so the server rejects it outright).
        """
        return self.champion_pool - self.unavailable() - self.fearless_blocked

    # --- ready check -----------------------------------------------------

    def set_ready(self, team: Team) -> bool:
        """Mark a captain as ready. Returns True if this started the draft."""
        if self.status != DraftStatus.WAITING:
            raise InvalidActionError("El draft ya ha comenzado.")
        self.ready[team] = True
        if all(self.ready.values()):
            self.status = DraftStatus.IN_PROGRESS
            return True
        return False

    # --- actions ---------------------------------------------------------

    def hover(self, team: Team, champion_id: str | None) -> None:
        """Set (or clear, with None) the acting captain's hovered champion."""
        self._require_turn(team)
        if champion_id is not None:
            self._require_selectable(champion_id)
        self.hovered = champion_id

    def confirm(self, team: Team, champion_id: str) -> TurnResult:
        self._require_turn(team)
        self._require_selectable(champion_id)
        return self._apply(champion_id, is_auto=False)

    def resolve_timeout(self) -> TurnResult:
        """Timer expired: confirm the hover, else random pick / skipped ban."""
        if self.status != DraftStatus.IN_PROGRESS:
            raise InvalidActionError("El draft no está en curso.")
        if self.hovered is not None:
            return self._apply(self.hovered, is_auto=True)
        _, action = DRAFT_SEQUENCE[self.turn_index]
        if action == ActionType.PICK:
            champion = self._rng.choice(sorted(self.selectable()))
            return self._apply(champion, is_auto=True)
        return self._apply(None, is_auto=True)  # skipped ban

    # --- post-draft lane assignment --------------------------------------

    def assign_lane(self, team: Team, pick_index: int, lane: str) -> int:
        """Assign a lane to one of a team's picks. Returns the pick's turn_index
        (so the caller can persist it on the matching DraftAction row)."""
        if self.status != DraftStatus.COMPLETED:
            raise InvalidActionError("El draft aún no ha terminado.")
        if lane not in LANES:
            raise InvalidActionError("Línea no válida.")
        if not 0 <= pick_index < len(self.picks[team]):
            raise InvalidActionError("Pick no válido.")
        self.lanes[team][pick_index] = lane
        return self.pick_turns[team][pick_index]

    # --- replay (rebuild from persisted actions) -------------------------

    def replay(self, results: list[TurnResult]) -> None:
        """Rebuild in-progress state from persisted actions, re-validating."""
        if self.status != DraftStatus.WAITING or self.turn_index != 0:
            raise InvalidActionError("Replay requires a fresh engine.")
        self.ready = {Team.BLUE: True, Team.RED: True}
        self.status = DraftStatus.IN_PROGRESS
        for result in results:
            if result.turn_index != self.turn_index:
                raise InvalidActionError("Replay actions out of order.")
            if result.champion_id is not None:
                self._require_selectable(result.champion_id)
            self._apply(
                result.champion_id, is_auto=result.is_auto, lane=result.lane
            )

    # --- internals -------------------------------------------------------

    def _require_turn(self, team: Team) -> None:
        if self.status == DraftStatus.WAITING:
            raise InvalidActionError("El draft aún no ha comenzado.")
        if self.status == DraftStatus.COMPLETED:
            raise InvalidActionError("El draft ya ha terminado.")
        current_team, _ = DRAFT_SEQUENCE[self.turn_index]
        if team != current_team:
            raise NotYourTurnError("No es tu turno.")

    def _require_selectable(self, champion_id: str) -> None:
        if champion_id not in self.champion_pool:
            raise ChampionUnavailableError("Ese campeón no existe.")
        if champion_id in self.fearless_blocked:
            raise ChampionUnavailableError(
                "Ese campeón está bloqueado por el modo Fearless."
            )
        if champion_id in self.unavailable():
            raise ChampionUnavailableError("Ese campeón ya no está disponible.")

    def _apply(
        self, champion_id: str | None, is_auto: bool, lane: str | None = None
    ) -> TurnResult:
        team, action = DRAFT_SEQUENCE[self.turn_index]
        if action == ActionType.BAN:
            self.bans[team].append(champion_id)
        else:
            if champion_id is None:
                raise InvalidActionError("A pick cannot be empty.")
            self.picks[team].append(champion_id)
            self.lanes[team].append(lane)
            self.pick_turns[team].append(self.turn_index)

        result = TurnResult(
            turn_index=self.turn_index,
            team=team,
            action_type=action,
            champion_id=champion_id,
            is_auto=is_auto,
            lane=lane if action == ActionType.PICK else None,
        )
        self.turn_index += 1
        self.hovered = None
        if self.turn_index >= TOTAL_TURNS:
            self.status = DraftStatus.COMPLETED
        return result
