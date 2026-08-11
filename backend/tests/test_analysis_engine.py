from app.analysis.engine import analyze
from app.analysis.types import AnalysisInput, TeamInput
from tests.conftest import make_profile

BLUE = ("BTop", "BJg", "BMid", "BBot", "BSup")
RED = ("RTop", "RJg", "RMid", "RBot", "RSup")
LANES = ("top", "jungle", "mid", "bot", "support")


def build_input(**overrides) -> AnalysisInput:
    profiles = {}
    for i, (b, r, lane) in enumerate(zip(BLUE, RED, LANES)):
        for j, cid in enumerate((b, r)):
            profiles[cid] = make_profile(
                cid,
                numeric_id=100 + i * 2 + j,
                lanes=(lane,),
                tags=("Marksman",) if lane == "bot" else ("Fighter",),
            )
    # Blue wins every lane 60/40 with a healthy sample.
    matchups = {}
    for i, lane in enumerate(LANES):
        blue_id, red_id = str(100 + i * 2), str(100 + i * 2 + 1)
        matchups[blue_id] = {lane: {red_id: [600, 1000]}}
    defaults = dict(
        blue=TeamInput(picks=BLUE, lanes=LANES),
        red=TeamInput(picks=RED, lanes=LANES),
        profiles=profiles,
        matchups=matchups,
        matchups_patch="16_15",
        matchups_stale=False,
        item_costs=(),
        phase_overrides={},
        patch="16.15.1",
    )
    defaults.update(overrides)
    return AnalysisInput(**defaults)


class TestAnalyze:
    def test_payload_shape(self):
        result = analyze(build_input())
        assert set(result) >= {
            "patch",
            "lanes_inferred",
            "partial",
            "lane_matchups",
            "compositions",
            "phases",
            "verdict",
        }
        assert len(result["lane_matchups"]["rows"]) == 5
        assert result["lane_matchups"]["available"] is True
        assert result["compositions"]["blue"]["scores"].keys() == {
            "engage", "poke", "peel", "frontline", "cc",
        }
        assert set(result["phases"]["blue"]) == {"pre15", "15to25", "post30"}
        assert len(result["phases"]["breakdown"]) == 10

    def test_blue_sweep_favors_blue(self):
        result = analyze(build_input())
        assert result["verdict"]["components"]["lanes"] > 0
        assert result["verdict"]["favors"] == "blue"

    def test_deterministic(self):
        assert analyze(build_input()) == analyze(build_input())

    def test_weights_sum_to_one(self):
        result = analyze(build_input())
        assert abs(sum(result["verdict"]["weights"].values()) - 1.0) < 0.01

    def test_no_matchups_redistributes_weights(self):
        result = analyze(build_input(matchups=None))
        assert result["lane_matchups"]["available"] is False
        assert result["lane_matchups"]["rows"] == []
        assert "lanes" not in result["verdict"]["components"]
        assert abs(sum(result["verdict"]["weights"].values()) - 1.0) < 0.01
        assert result["partial"] is True

    def test_missing_lanes_are_inferred(self):
        result = analyze(
            build_input(blue=TeamInput(picks=BLUE, lanes=(None,) * 5))
        )
        assert result["lanes_inferred"] is True
        assert len(result["lane_matchups"]["rows"]) == 5
        # Profiles pin each champion to one lane, so inference recovers them
        # and the matchup rows still find data.
        assert all(
            row["winrate_blue"] is not None
            for row in result["lane_matchups"]["rows"]
        )

    def test_mirror_comps_are_even(self):
        # Identical matchup-less input -> composition and phases cancel out.
        result = analyze(build_input(matchups=None))
        assert result["verdict"]["components"]["composition"] == 0
        assert result["verdict"]["components"]["phases"] == 0
        assert result["verdict"]["tier"] == "even"
