"""Per-lane 1v1 matchup winrates with sample-size shrinkage.

The u.gg numbers are raw (wins, games) per opponent per lane. Small samples
would swing wildly, so every winrate is shrunk toward 50% with K pseudo-games
(a Bayesian prior): adj = (wins + K/2) / (games + K). When both champions'
files carry the mirror matchup we average the two directions weighted by their
sample sizes.
"""

from dataclasses import dataclass

from .types import LANE_ORDER, MatchupTable

SHRINK_K = 50
CONFIDENCE_TIERS = ((200, "alta"), (50, "media"), (1, "baja"))


def shrunk_winrate(wins: int, games: int) -> float:
    return (wins + SHRINK_K / 2) / (games + SHRINK_K)


def confidence_for(games: int) -> str:
    for threshold, label in CONFIDENCE_TIERS:
        if games >= threshold:
            return label
    return "sin_datos"


@dataclass
class LaneMatchup:
    lane: str
    blue_champion: str
    red_champion: str
    winrate_blue: float | None  # shrunk, 0-100; None = no data at all
    wins: int
    games: int
    confidence: str  # 'alta' | 'media' | 'baja' | 'sin_datos'
    inferred: bool  # True if either lane assignment was inferred

    def delta_weighted(self) -> float:
        """Confidence-weighted advantage in [-0.5, 0.5] for the verdict."""
        if self.winrate_blue is None:
            return 0.0
        weight = self.games / (self.games + SHRINK_K)
        return (self.winrate_blue / 100 - 0.5) * weight


def _lookup(
    table: MatchupTable, champ: int | None, lane: str, opponent: int | None
) -> tuple[int, int] | None:
    if champ is None or opponent is None:
        return None
    row = table.get(str(champ), {}).get(lane, {}).get(str(opponent))
    if row is None:
        return None
    return row[0], row[1]


def compute_lane_matchups(
    blue_by_lane: dict[str, str],
    red_by_lane: dict[str, str],
    numeric_ids: dict[str, int | None],
    table: MatchupTable,
    inferred_lanes: set[str],
) -> list[LaneMatchup]:
    rows: list[LaneMatchup] = []
    for lane in LANE_ORDER:
        blue = blue_by_lane.get(lane)
        red = red_by_lane.get(lane)
        if blue is None or red is None:
            continue
        blue_id = numeric_ids.get(blue)
        red_id = numeric_ids.get(red)

        direct = _lookup(table, blue_id, lane, red_id)  # blue's wins vs red
        mirror = _lookup(table, red_id, lane, blue_id)  # red's wins vs blue

        wins = games = 0
        winrate: float | None = None
        if direct and mirror:
            d_wins, d_games = direct
            m_wins, m_games = mirror
            games = d_games + m_games
            # Weighted average of the two directions (mirror inverted).
            winrate = (
                shrunk_winrate(d_wins, d_games) * d_games
                + (1 - shrunk_winrate(m_wins, m_games)) * m_games
            ) / games * 100
            wins = d_wins + (m_games - m_wins)
        elif direct:
            wins, games = direct
            winrate = shrunk_winrate(wins, games) * 100
        elif mirror:
            m_wins, m_games = mirror
            wins, games = m_games - m_wins, m_games
            winrate = (1 - shrunk_winrate(m_wins, m_games)) * 100

        rows.append(
            LaneMatchup(
                lane=lane,
                blue_champion=blue,
                red_champion=red,
                winrate_blue=round(winrate, 1) if winrate is not None else None,
                wins=wins,
                games=games,
                confidence=confidence_for(games) if winrate is not None else "sin_datos",
                inferred=lane in inferred_lanes,
            )
        )
    return rows
