from app.analysis.spikes import (
    CLASS_CURVES,
    PHASES,
    champion_curve,
    load_overrides,
    median_core_cost,
    team_phase_scores,
)
from tests.conftest import make_profile

CHEAP_AD = ({"name": "Cheap", "total": 2100, "kind": "AD"},)
PRICEY_AD = ({"name": "Pricey", "total": 5500, "kind": "AD"},)


class TestOverridesFile:
    def test_curated_file_is_sane(self):
        overrides = load_overrides()
        assert len(overrides) >= 40
        for cid, curve in overrides.items():
            assert set(curve) == set(PHASES), cid
            assert all(0 <= curve[p] <= 100 for p in PHASES), cid

    def test_missing_file_returns_empty(self, tmp_path):
        assert load_overrides(tmp_path / "nope.json") == {}


class TestChampionCurve:
    def test_override_beats_heuristic(self):
        overrides = {"Kayle": {"pre15": 20, "15to25": 45, "post30": 95}}
        curve = champion_curve(
            make_profile("Kayle", tags=("Fighter",)), "Kayle", "top", overrides, ()
        )
        assert curve.source == "override"
        assert curve.curve["post30"] == 95

    def test_class_heuristic_without_items(self):
        curve = champion_curve(
            make_profile("X", tags=("Marksman",)), "X", "bot", {}, ()
        )
        assert curve.source == "heuristic"
        assert curve.curve == CLASS_CURVES["Marksman"]

    def test_cheap_core_shifts_early(self):
        base = CLASS_CURVES["Marksman"]
        curve = champion_curve(
            make_profile("X", tags=("Marksman",), ratings={"damage": 3}),
            "X",
            "bot",
            {},
            CHEAP_AD,  # 2*2100/420 = 10 min core
        )
        assert curve.curve["pre15"] == base["pre15"] + 10
        assert curve.curve["post30"] == base["post30"] - 5

    def test_pricey_core_shifts_late(self):
        base = CLASS_CURVES["Marksman"]
        curve = champion_curve(
            make_profile("X", tags=("Marksman",), ratings={"damage": 3}),
            "X",
            "bot",
            {},
            PRICEY_AD,  # 2*5500/420 = 26+ min core
        )
        assert curve.curve["pre15"] == base["pre15"] - 10
        assert curve.curve["post30"] == base["post30"] + 10

    def test_low_damage_champion_ignores_items(self):
        curve = champion_curve(
            make_profile("X", tags=("Tank",), ratings={"damage": 1}),
            "X",
            "top",
            {},
            CHEAP_AD,
        )
        assert curve.curve == CLASS_CURVES["Tank"]

    def test_unknown_profile_gets_default(self):
        curve = champion_curve(None, "Mystery", None, {}, ())
        assert curve.source == "heuristic"
        assert set(curve.curve) == set(PHASES)

    def test_lane_weight(self):
        assert champion_curve(None, "X", "bot", {}, ()).weight == 1.2
        assert champion_curve(None, "X", "support", {}, ()).weight == 0.6
        assert champion_curve(None, "X", None, {}, ()).weight == 1.0


class TestMedianCost:
    def test_filters_by_kind(self):
        items = (
            {"name": "a", "total": 3000, "kind": "AD"},
            {"name": "b", "total": 4000, "kind": "AP"},
        )
        assert median_core_cost(items, "PHYSICAL_DAMAGE") == 3000
        assert median_core_cost(items, "MAGIC_DAMAGE") == 4000
        assert median_core_cost(items, None) == 3500  # no filter -> all
        assert median_core_cost((), "PHYSICAL_DAMAGE") is None


class TestTeamScores:
    def test_weighted_mean(self):
        curves = [
            champion_curve(None, "A", "bot", {"A": {"pre15": 100, "15to25": 100, "post30": 100}}, ()),
            champion_curve(None, "B", "support", {"B": {"pre15": 0, "15to25": 0, "post30": 0}}, ()),
        ]
        scores = team_phase_scores(curves)
        # bot weighs 1.2 vs support 0.6 -> 100*1.2/1.8 = 67
        assert scores["pre15"] == 67

    def test_empty(self):
        assert team_phase_scores([]) == {p: 0 for p in PHASES}
