"""Power-spike curves per phase (pre-15 / 15-25 / 30+) and team phase scores.

No free keyless source publishes winrate-by-game-minute, so each champion gets
a 0-100 score per phase from, in priority order:
1. data/phase_overrides.json — curated outliers (Kayle, Draven, ...), wins always;
2. a class heuristic from Data Dragon tags, nudged by how expensive a typical
   completed damage item is for the champion's damage type (cheaper core =
   earlier spike).

Team score per phase = weighted mean over the five champions (carries weigh
more: bot/mid 1.2, top/jungle 1.0, support 0.6).
"""

import json
from dataclasses import dataclass
from pathlib import Path
from statistics import median

from .types import ChampionProfile

PHASES = ("pre15", "15to25", "post30")
OVERRIDES_PATH = Path(__file__).resolve().parent / "data" / "phase_overrides.json"

# Baseline curves per Data Dragon primary class.
CLASS_CURVES: dict[str, dict[str, int]] = {
    "Marksman": {"pre15": 35, "15to25": 55, "post30": 90},
    "Assassin": {"pre15": 55, "15to25": 80, "post30": 55},
    "Mage": {"pre15": 45, "15to25": 70, "post30": 70},
    "Fighter": {"pre15": 65, "15to25": 70, "post30": 55},
    "Tank": {"pre15": 50, "15to25": 70, "post30": 65},
    "Support": {"pre15": 55, "15to25": 60, "post30": 65},
}
DEFAULT_CURVE = {"pre15": 50, "15to25": 60, "post30": 60}

LANE_WEIGHTS = {"top": 1.0, "jungle": 1.0, "mid": 1.2, "bot": 1.2, "support": 0.6}

# Gold pacing for the item nudge: two completed items is the classic mid-game
# spike; ~420 g/min is an average carry income.
GOLD_PER_MINUTE = 420
CORE_ITEMS = 2
EARLY_CORE_MINUTE = 15
LATE_CORE_MINUTE = 25
ADVANTAGE_THRESHOLD = 8  # |delta| >= this -> phase advantage


def load_overrides(path: Path = OVERRIDES_PATH) -> dict[str, dict[str, int]]:
    try:
        with open(path, encoding="utf-8") as fh:
            raw = json.load(fh)
    except (OSError, ValueError):
        return {}
    return {
        cid: curve
        for cid, curve in raw.items()
        if not cid.startswith("_")
        and isinstance(curve, dict)
        and all(p in curve and isinstance(curve[p], int) for p in PHASES)
    }


def median_core_cost(item_costs: tuple[dict, ...], damage_type: str | None) -> float | None:
    kind = {"PHYSICAL_DAMAGE": "AD", "MAGIC_DAMAGE": "AP"}.get(damage_type or "")
    totals = [
        i["total"]
        for i in item_costs
        if isinstance(i.get("total"), int) and (kind is None or i.get("kind") == kind)
    ]
    return median(totals) if totals else None


@dataclass
class ChampionCurve:
    champion_id: str
    curve: dict[str, int]
    source: str  # 'override' | 'heuristic'
    weight: float


def champion_curve(
    profile: ChampionProfile | None,
    champion_id: str,
    lane: str | None,
    overrides: dict[str, dict[str, int]],
    item_costs: tuple[dict, ...],
) -> ChampionCurve:
    weight = LANE_WEIGHTS.get(lane or "", 1.0)
    if champion_id in overrides:
        return ChampionCurve(champion_id, dict(overrides[champion_id]), "override", weight)

    primary_tag = profile.tags[0] if profile and profile.tags else None
    curve = dict(CLASS_CURVES.get(primary_tag or "", DEFAULT_CURVE))

    # Item nudge, only for champions whose output is item-bound (damage >= 2).
    if profile and profile.ratings.get("damage", 0) >= 2:
        cost = median_core_cost(item_costs, profile.damage_type)
        if cost is not None:
            core_minute = CORE_ITEMS * cost / GOLD_PER_MINUTE
            if core_minute <= EARLY_CORE_MINUTE:
                curve["pre15"] = min(100, curve["pre15"] + 10)
                curve["post30"] = max(0, curve["post30"] - 5)
            elif core_minute >= LATE_CORE_MINUTE:
                curve["pre15"] = max(0, curve["pre15"] - 10)
                curve["post30"] = min(100, curve["post30"] + 10)
    return ChampionCurve(champion_id, curve, "heuristic", weight)


def team_phase_scores(curves: list[ChampionCurve]) -> dict[str, int]:
    total_weight = sum(c.weight for c in curves)
    if not total_weight:
        return {p: 0 for p in PHASES}
    return {
        p: round(sum(c.curve[p] * c.weight for c in curves) / total_weight)
        for p in PHASES
    }
