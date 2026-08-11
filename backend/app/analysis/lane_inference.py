"""Fill in unassigned lanes so the matchup table can still be computed.

Captains may skip the post-draft lane picker entirely. When lanes are missing
we solve the pick->lane assignment against the Meraki position catalog:
forced singletons first, then a deterministic brute force over the remaining
permutations (<= 5! = 120) maximizing "champion actually plays that lane"
hits. Inferred lanes are flagged so the UI and confidence scoring can
discount them.
"""

from itertools import permutations

from .types import LANE_ORDER, ChampionProfile


def infer_lanes(
    picks: tuple[str, ...],
    assigned: tuple[str | None, ...],
    profiles: dict[str, ChampionProfile],
) -> tuple[list[str | None], bool]:
    """Returns (lanes aligned with picks, any_inferred)."""
    lanes: list[str | None] = list(assigned)
    if all(lane is not None for lane in lanes):
        return lanes, False

    free_lanes = [lane for lane in LANE_ORDER if lane not in lanes]
    open_idx = [i for i, lane in enumerate(lanes) if lane is None]

    def candidates(pick: str) -> list[str]:
        known = profiles.get(pick)
        if known is None or not known.lanes:
            return list(free_lanes)  # unknown champion: anything goes
        playable = [lane for lane in known.lanes if lane in free_lanes]
        return playable or list(free_lanes)

    # Forced singletons: a pick with one candidate lane, or a lane wanted by
    # exactly one pick. Repeat until stable.
    changed = True
    while changed and open_idx:
        changed = False
        for i in list(open_idx):
            cands = candidates(picks[i])
            if len(cands) == 1:
                lanes[i] = cands[0]
                free_lanes.remove(cands[0])
                open_idx.remove(i)
                changed = True
        for lane in list(free_lanes):
            wanters = [i for i in open_idx if lane in candidates(picks[i])]
            if len(wanters) == 1:
                lanes[wanters[0]] = lane
                free_lanes.remove(lane)
                open_idx.remove(wanters[0])
                changed = True

    if open_idx:
        # Deterministic brute force: score by primary-position hits; ties break
        # by permutation order over LANE_ORDER, which is stable.
        def score(assignment: tuple[str, ...]) -> int:
            total = 0
            for i, lane in zip(open_idx, assignment):
                known = profiles.get(picks[i])
                if known is None or not known.lanes:
                    continue
                if lane in known.lanes:
                    # Earlier positions in Meraki's list are the champion's
                    # main lanes; reward them slightly more.
                    total += 10 - known.lanes.index(lane)
            return total

        best = max(permutations(free_lanes, len(open_idx)), key=score)
        for i, lane in zip(open_idx, best):
            lanes[i] = lane

    return lanes, True
