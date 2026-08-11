import json
from pathlib import Path

from app.analysis.matchups import (
    SHRINK_K,
    compute_lane_matchups,
    confidence_for,
    shrunk_winrate,
)

FIXTURE = json.loads(
    (Path(__file__).parent / "fixtures" / "ugg_matchups_sample.json").read_text(
        encoding="utf-8"
    )
)


class TestShrinkage:
    def test_even_record_stays_at_50(self):
        assert shrunk_winrate(50, 100) == 0.5

    def test_small_sample_pulled_toward_50(self):
        # 10/10 raw would be 100%; shrunk it barely crosses 58%.
        assert shrunk_winrate(10, 10) == (10 + SHRINK_K / 2) / (10 + SHRINK_K)
        assert shrunk_winrate(10, 10) < 0.6

    def test_large_sample_barely_moves(self):
        assert abs(shrunk_winrate(6000, 10000) - 0.6) < 0.005


class TestConfidence:
    def test_tiers(self):
        assert confidence_for(500) == "alta"
        assert confidence_for(200) == "alta"
        assert confidence_for(199) == "media"
        assert confidence_for(50) == "media"
        assert confidence_for(49) == "baja"
        assert confidence_for(1) == "baja"
        assert confidence_for(0) == "sin_datos"


def _rows(**kwargs):
    defaults = dict(
        blue_by_lane={"top": "BlueTop"},
        red_by_lane={"top": "RedTop"},
        numeric_ids={"BlueTop": 1, "RedTop": 2},
        table={},
        inferred_lanes=set(),
    )
    defaults.update(kwargs)
    return compute_lane_matchups(**defaults)


class TestLaneMatchups:
    def test_direct_only(self):
        rows = _rows(table={"1": {"top": {"2": [60, 100]}}})
        assert len(rows) == 1
        row = rows[0]
        assert row.lane == "top"
        assert row.games == 100
        assert row.winrate_blue == round(shrunk_winrate(60, 100) * 100, 1)
        assert row.confidence == "media"

    def test_mirror_only_inverts_direction(self):
        # Red's file says red wins 60% vs blue -> blue is below 50%.
        rows = _rows(table={"2": {"top": {"1": [60, 100]}}})
        assert rows[0].winrate_blue < 50
        assert rows[0].games == 100

    def test_both_directions_average(self):
        rows = _rows(
            table={
                "1": {"top": {"2": [60, 100]}},
                "2": {"top": {"1": [40, 100]}},
            }
        )
        row = rows[0]
        assert row.games == 200
        # Both directions agree on blue ~60% raw; shrunk value sits below it.
        assert 55 < row.winrate_blue < 60

    def test_missing_matchup_is_sin_datos(self):
        row = _rows()[0]
        assert row.winrate_blue is None
        assert row.confidence == "sin_datos"
        assert row.delta_weighted() == 0.0

    def test_unknown_numeric_id_is_sin_datos(self):
        row = _rows(numeric_ids={"BlueTop": None, "RedTop": 2})[0]
        assert row.winrate_blue is None

    def test_inferred_flag(self):
        row = _rows(inferred_lanes={"top"})[0]
        assert row.inferred is True

    def test_real_fixture_direction(self):
        # Jinx (222) vs Caitlyn (51) bot on the real snapshot: 65476/134202,
        # a famously rough lane — must stay below 50% after shrinkage.
        rows = compute_lane_matchups(
            blue_by_lane={"bot": "Jinx"},
            red_by_lane={"bot": "Caitlyn"},
            numeric_ids={"Jinx": 222, "Caitlyn": 51},
            table=FIXTURE["champions"],
            inferred_lanes=set(),
        )
        row = rows[0]
        assert row.games == 134202
        assert 48 < row.winrate_blue < 50
        assert row.confidence == "alta"
        assert row.delta_weighted() < 0
