"""Team composition profiling from Riot's 0-3 champion attribute ratings.

Sub-scores per champion (0-3 scale) combine the ratings with weights chosen so
canonical examples land where a player expects (Malphite/Leona high engage,
enchanters high peel, artillery mages high poke). Team scores normalize to
0-100 over the champions that actually have data, so one unknown champion
degrades the score instead of zeroing it.
"""

from dataclasses import dataclass, field

from .types import ChampionProfile

MAX_RATING = 3
ARCHETYPES = ("engage", "poke", "peel")
SECONDARY_MARGIN = 15  # archetype within this many points of primary
FLEXIBLE_THRESHOLD = 40  # all archetype scores below this -> 'flexible'
DAMAGE_WARNING_COUNT = 4  # this many champs sharing a damage type -> warning


def champion_subscores(profile: ChampionProfile) -> dict[str, float] | None:
    r = profile.ratings
    if not r:
        return None
    control = r.get("control", 0)
    mobility = r.get("mobility", 0)
    toughness = r.get("toughness", 0)
    utility = r.get("utility", 0)
    damage = r.get("damage", 0)
    ranged = 1.0 if profile.attack_type == "RANGED" else 0.0
    return {
        "frontline": float(toughness),
        "engage": 0.5 * control + 0.3 * mobility + 0.2 * toughness,
        "peel": 0.5 * control + 0.5 * utility,
        "poke": ranged * (0.6 * damage + 0.4 * (MAX_RATING - toughness)),
        "cc": float(control),
    }


@dataclass
class TeamComposition:
    scores: dict[str, int]  # engage/poke/peel/frontline/cc, 0-100
    ranged_count: int
    avg_attack_range: int | None
    damage_mix: dict[str, int]  # physical / magic / mixed counts
    damage_warning: str | None  # internal code, frontend translates
    archetype_primary: str  # 'engage'|'poke'|'peel'|'flexible'
    archetype_secondary: str | None
    breakdown: list[dict] = field(default_factory=list)  # per-champion subscores
    partial: bool = False  # some champion had no ratings data


_DAMAGE_KEY = {
    "PHYSICAL_DAMAGE": "physical",
    "MAGIC_DAMAGE": "magic",
    "MIXED_DAMAGE": "mixed",
}


def profile_team(picks: tuple[str, ...], profiles: dict[str, ChampionProfile]) -> TeamComposition:
    per_champ: list[tuple[str, dict[str, float] | None]] = [
        (pick, champion_subscores(profiles[pick]) if pick in profiles else None)
        for pick in picks
    ]
    with_data = [scores for _, scores in per_champ if scores is not None]
    partial = len(with_data) < len(picks)

    scores: dict[str, int] = {}
    for metric in ("engage", "poke", "peel", "frontline", "cc"):
        if with_data:
            total = sum(s[metric] for s in with_data)
            scores[metric] = round(100 * total / (len(with_data) * MAX_RATING))
        else:
            scores[metric] = 0

    ranged = [
        profiles[pick]
        for pick in picks
        if pick in profiles and profiles[pick].attack_type == "RANGED"
    ]
    known_ranges = [
        profiles[pick].attack_range
        for pick in picks
        if pick in profiles and profiles[pick].attack_range
    ]

    damage_mix = {"physical": 0, "magic": 0, "mixed": 0}
    for pick in picks:
        key = _DAMAGE_KEY.get(profiles[pick].damage_type) if pick in profiles else None
        if key:
            damage_mix[key] += 1
    warning = None
    if damage_mix["physical"] >= DAMAGE_WARNING_COUNT:
        warning = "mostly_physical"
    elif damage_mix["magic"] >= DAMAGE_WARNING_COUNT:
        warning = "mostly_magic"

    primary = max(ARCHETYPES, key=lambda a: scores[a])
    if scores[primary] < FLEXIBLE_THRESHOLD:
        primary_label, secondary = "flexible", None
    else:
        primary_label = primary
        runners = sorted(
            (a for a in ARCHETYPES if a != primary), key=lambda a: -scores[a]
        )
        secondary = (
            runners[0]
            if runners and scores[primary] - scores[runners[0]] <= SECONDARY_MARGIN
            and scores[runners[0]] >= FLEXIBLE_THRESHOLD
            else None
        )

    return TeamComposition(
        scores=scores,
        ranged_count=len(ranged),
        avg_attack_range=round(sum(known_ranges) / len(known_ranges)) if known_ranges else None,
        damage_mix=damage_mix,
        damage_warning=warning,
        archetype_primary=primary_label,
        archetype_secondary=secondary,
        breakdown=[
            {
                "champion_id": pick,
                **({k: round(v, 2) for k, v in subs.items()} if subs else {}),
                "missing": subs is None,
            }
            for pick, subs in per_champ
        ],
        partial=partial,
    )


# Transparent counter triangle for the verdict: engage beats poke (dives the
# siege), poke beats peel (whittles from range), peel beats engage (stops the
# dive). Returns a bonus in [-1, 1] from blue's perspective.
_COUNTERS = {("engage", "poke"), ("poke", "peel"), ("peel", "engage")}


def archetype_counter_bonus(blue_primary: str, red_primary: str) -> int:
    if (blue_primary, red_primary) in _COUNTERS:
        return 1
    if (red_primary, blue_primary) in _COUNTERS:
        return -1
    return 0
