"""Pure draft-analysis engine: AnalysisInput in, JSON-ready dict out.

Mirrors draft/engine.py's contract with the rest of the app: no IO, no
framework imports, fully deterministic, unit-tested. Every number in the
output ships with the inputs that produced it — the verdict must always be
explainable from the payload alone.
"""

from dataclasses import asdict

from .composition import archetype_counter_bonus, profile_team
from .lane_inference import infer_lanes
from .matchups import compute_lane_matchups
from .spikes import ADVANTAGE_THRESHOLD, PHASES, champion_curve, team_phase_scores
from .types import AnalysisInput, TeamInput

# Verdict component weights (redistributed when a section has no data).
BASE_WEIGHTS = {"lanes": 0.5, "composition": 0.25, "phases": 0.25}
# Verdict tiers on the total score.
TIER_EVEN = 1.5
TIER_SLIGHT = 4.0
COUNTER_BONUS_POINTS = 3.0


def _resolve_lanes(team: TeamInput, inp: AnalysisInput) -> tuple[dict[str, str], set[str], bool]:
    lanes, inferred = infer_lanes(team.picks, team.lanes, inp.profiles)
    by_lane = {lane: pick for pick, lane in zip(team.picks, lanes) if lane}
    inferred_lanes = (
        {lane for lane, prev in zip(lanes, team.lanes) if prev is None and lane}
        if inferred
        else set()
    )
    return by_lane, inferred_lanes, inferred


def analyze(inp: AnalysisInput) -> dict:
    blue_by_lane, blue_inferred, blue_any_inf = _resolve_lanes(inp.blue, inp)
    red_by_lane, red_inferred, red_any_inf = _resolve_lanes(inp.red, inp)
    lanes_inferred = blue_any_inf or red_any_inf

    numeric_ids = {
        cid: (inp.profiles[cid].numeric_id if cid in inp.profiles else None)
        for cid in (*inp.blue.picks, *inp.red.picks)
    }

    # --- lane matchups ---------------------------------------------------
    matchup_rows = []
    matchups_available = inp.matchups is not None
    if matchups_available:
        matchup_rows = compute_lane_matchups(
            blue_by_lane,
            red_by_lane,
            numeric_ids,
            inp.matchups,
            blue_inferred | red_inferred,
        )

    # --- compositions ----------------------------------------------------
    blue_comp = profile_team(inp.blue.picks, inp.profiles)
    red_comp = profile_team(inp.red.picks, inp.profiles)
    comps_available = not (blue_comp.partial and red_comp.partial and not inp.profiles)

    # --- phases ----------------------------------------------------------
    def curves_for(team: TeamInput, by_lane: dict[str, str]) -> list:
        lane_of = {pick: lane for lane, pick in by_lane.items()}
        return [
            champion_curve(
                inp.profiles.get(pick), pick, lane_of.get(pick), inp.phase_overrides, inp.item_costs
            )
            for pick in team.picks
        ]

    blue_curves = curves_for(inp.blue, blue_by_lane)
    red_curves = curves_for(inp.red, red_by_lane)
    blue_phases = team_phase_scores(blue_curves)
    red_phases = team_phase_scores(red_curves)
    phase_deltas = {p: blue_phases[p] - red_phases[p] for p in PHASES}

    # --- verdict ---------------------------------------------------------
    components: dict[str, float] = {}
    if matchups_available and matchup_rows:
        # Sum of confidence-weighted lane deltas, scaled so five one-sided
        # high-confidence lanes max out around +/-10.
        components["lanes"] = round(
            sum(row.delta_weighted() for row in matchup_rows) * 20, 2
        )
    if comps_available:
        counter = archetype_counter_bonus(
            blue_comp.archetype_primary, red_comp.archetype_primary
        )
        coherence = (
            max(blue_comp.scores[a] for a in ("engage", "poke", "peel"))
            - max(red_comp.scores[a] for a in ("engage", "poke", "peel"))
        ) / 50  # -2..2: how much more defined blue's identity is
        components["composition"] = round(
            max(-5.0, min(5.0, counter * COUNTER_BONUS_POINTS + coherence)), 2
        )
    components["phases"] = round(
        max(-5.0, min(5.0, sum(phase_deltas.values()) / (len(PHASES) * 10) * 5)), 2
    )

    weights = {k: BASE_WEIGHTS[k] for k in components}
    total_weight = sum(weights.values())
    weights = {k: round(w / total_weight, 3) for k, w in weights.items()}
    total = sum(components[k] * weights[k] / BASE_WEIGHTS[k] for k in components)

    if abs(total) < TIER_EVEN:
        tier, favors = "even", None
    else:
        tier = "slight" if abs(total) < TIER_SLIGHT else "clear"
        favors = "blue" if total > 0 else "red"

    return {
        "patch": inp.patch,
        "lanes_inferred": lanes_inferred,
        "partial": blue_comp.partial or red_comp.partial or not matchups_available,
        "lane_matchups": {
            "available": matchups_available,
            "stale": inp.matchups_stale,
            "snapshot_patch": inp.matchups_patch,
            "rows": [
                {
                    "lane": row.lane,
                    "blue_champion": row.blue_champion,
                    "red_champion": row.red_champion,
                    "winrate_blue": row.winrate_blue,
                    "wins": row.wins,
                    "games": row.games,
                    "confidence": row.confidence,
                    "inferred": row.inferred,
                }
                for row in matchup_rows
            ],
        },
        "compositions": {
            "available": comps_available,
            "stale": inp.profiles_stale,
            "blue": asdict(blue_comp),
            "red": asdict(red_comp),
        },
        "phases": {
            "available": True,
            "blue": blue_phases,
            "red": red_phases,
            "deltas": phase_deltas,
            "advantage_threshold": ADVANTAGE_THRESHOLD,
            "breakdown": [
                {
                    "team": team,
                    "champion_id": c.champion_id,
                    "curve": c.curve,
                    "source": c.source,
                    "weight": c.weight,
                }
                for team, curves in (("blue", blue_curves), ("red", red_curves))
                for c in curves
            ],
        },
        "verdict": {
            "total": round(total, 2),
            "tier": tier,
            "favors": favors,
            "components": components,
            "weights": weights,
        },
    }
