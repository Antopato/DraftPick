import random

import pytest

from app.analysis.types import ChampionProfile
from app.draft.engine import DraftEngine
from app.draft.sequence import DRAFT_SEQUENCE, Team

POOL = {f"Champ{i:02d}" for i in range(60)}


def make_profile(champion_id: str, **overrides) -> ChampionProfile:
    """Champion profile with sane defaults for analysis tests."""
    defaults = dict(
        champion_id=champion_id,
        numeric_id=abs(hash(champion_id)) % 1000,
        tags=("Fighter",),
        lanes=("top",),
        attack_type="MELEE",
        attack_range=175.0,
        damage_type="PHYSICAL_DAMAGE",
        ratings={"damage": 2, "toughness": 2, "control": 1, "mobility": 1, "utility": 1},
    )
    defaults.update(overrides)
    return ChampionProfile(**defaults)


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
