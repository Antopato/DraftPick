"""Pure data types for the draft analysis engine (no IO, no framework)."""

from dataclasses import dataclass, field

LANE_ORDER = ["top", "jungle", "mid", "bot", "support"]

# {numeric_id(str): {lane: {opponent_numeric_id(str): [wins, games]}}}
MatchupTable = dict[str, dict[str, dict[str, list[int]]]]


@dataclass(frozen=True)
class ChampionProfile:
    """Everything the analysis knows about one champion. Fields are optional
    on purpose: a missing profile (or missing field) lowers confidence instead
    of failing."""

    champion_id: str
    numeric_id: int | None = None
    tags: tuple[str, ...] = ()  # Data Dragon classes, e.g. ('Fighter', 'Tank')
    lanes: tuple[str, ...] = ()  # Meraki positions (internal lane codes)
    attack_type: str | None = None  # 'MELEE' | 'RANGED'
    attack_range: float | None = None
    damage_type: str | None = None  # 'PHYSICAL_DAMAGE' | 'MAGIC_DAMAGE' | 'MIXED_DAMAGE'
    # Riot 0-3 scales: damage, toughness, control, mobility, utility.
    ratings: dict[str, int] = field(default_factory=dict)


@dataclass(frozen=True)
class TeamInput:
    picks: tuple[str, ...]  # 5 champion ids, pick order
    lanes: tuple[str | None, ...]  # aligned with picks; None = unassigned


@dataclass(frozen=True)
class AnalysisInput:
    blue: TeamInput
    red: TeamInput
    profiles: dict[str, ChampionProfile]  # by champion_id; entries may be missing
    matchups: MatchupTable | None  # None = no snapshot available
    matchups_patch: str | None = None  # u.gg patch of the snapshot served
    matchups_stale: bool = False
    item_costs: tuple[dict, ...] = ()  # [{'name', 'total', 'kind'}] legendaries
    profiles_stale: bool = False
    phase_overrides: dict[str, dict[str, int]] = field(default_factory=dict)
    patch: str = ""  # Data Dragon version, e.g. '16.15.1'
