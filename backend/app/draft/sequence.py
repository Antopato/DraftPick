"""Standard tournament draft sequence. This order is a hard invariant — never change it.

Ban phase 1:  B R B R B R          (6 bans)
Pick phase 1: B1 · R1 R2 · B2 B3 · R3
Ban phase 2:  R B R B              (4 bans)
Pick phase 2: R4 · B4 B5 · R5
"""

from enum import Enum


class Team(str, Enum):
    BLUE = "blue"
    RED = "red"


class ActionType(str, Enum):
    BAN = "ban"
    PICK = "pick"


_B, _R = Team.BLUE, Team.RED
_BAN, _PICK = ActionType.BAN, ActionType.PICK

DRAFT_SEQUENCE: tuple[tuple[Team, ActionType], ...] = (
    # Ban phase 1
    (_B, _BAN), (_R, _BAN), (_B, _BAN), (_R, _BAN), (_B, _BAN), (_R, _BAN),
    # Pick phase 1: B1, R1, R2, B2, B3, R3
    (_B, _PICK), (_R, _PICK), (_R, _PICK), (_B, _PICK), (_B, _PICK), (_R, _PICK),
    # Ban phase 2
    (_R, _BAN), (_B, _BAN), (_R, _BAN), (_B, _BAN),
    # Pick phase 2: R4, B4, B5, R5
    (_R, _PICK), (_B, _PICK), (_B, _PICK), (_R, _PICK),
)

TOTAL_TURNS = len(DRAFT_SEQUENCE)  # 20


def slot_number(turn_index: int) -> int:
    """1-based slot within its own kind for the acting team at this turn.

    E.g. turn 0 -> blue ban 1, turn 19 -> red pick 5. Used for UI labels like
    'TURNO ACTUAL: ROJO — BAN 3'.
    """
    team, action = DRAFT_SEQUENCE[turn_index]
    return (
        sum(
            1
            for t, a in DRAFT_SEQUENCE[: turn_index + 1]
            if t == team and a == action
        )
    )
