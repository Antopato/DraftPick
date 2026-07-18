import random

import pytest

from app.draft.engine import DraftEngine
from app.draft.sequence import DRAFT_SEQUENCE, Team

POOL = {f"Champ{i:02d}" for i in range(60)}


@pytest.fixture
def engine() -> DraftEngine:
    e = DraftEngine(champion_pool=set(POOL), rng=random.Random(42))
    e.set_ready(Team.BLUE)
    e.set_ready(Team.RED)
    return e


def play_turns(engine: DraftEngine, count: int) -> list[str]:
    """Confirm `count` turns with arbitrary distinct legal champions."""
    used: list[str] = []
    for _ in range(count):
        team, _action = DRAFT_SEQUENCE[engine.turn_index]
        champion = sorted(engine.selectable())[0]
        engine.confirm(team, champion)
        used.append(champion)
    return used
