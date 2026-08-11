from app.analysis.composition import (
    archetype_counter_bonus,
    champion_subscores,
    profile_team,
)
from tests.conftest import make_profile


def tank(cid):
    return make_profile(
        cid,
        attack_type="MELEE",
        ratings={"damage": 1, "toughness": 3, "control": 3, "mobility": 2, "utility": 1},
    )


def artillery(cid):
    return make_profile(
        cid,
        attack_type="RANGED",
        attack_range=600.0,
        damage_type="MAGIC_DAMAGE",
        ratings={"damage": 3, "toughness": 1, "control": 1, "mobility": 1, "utility": 1},
    )


def enchanter(cid):
    return make_profile(
        cid,
        attack_type="RANGED",
        attack_range=550.0,
        damage_type="MAGIC_DAMAGE",
        ratings={"damage": 1, "toughness": 1, "control": 2, "mobility": 1, "utility": 3},
    )


class TestSubscores:
    def test_tank_engages_melee_never_pokes(self):
        subs = champion_subscores(tank("Malphite"))
        assert subs["engage"] > 2
        assert subs["poke"] == 0.0

    def test_no_ratings_returns_none(self):
        assert champion_subscores(make_profile("X", ratings={})) is None


class TestTeamProfile:
    def test_five_tanks_classify_engage(self):
        comp = profile_team(tuple(f"T{i}" for i in range(5)), {f"T{i}": tank(f"T{i}") for i in range(5)})
        assert comp.archetype_primary == "engage"
        assert comp.scores["engage"] >= 70
        assert comp.ranged_count == 0
        assert comp.partial is False

    def test_ranged_damage_team_classifies_poke(self):
        comp = profile_team(
            tuple(f"P{i}" for i in range(5)),
            {f"P{i}": artillery(f"P{i}") for i in range(5)},
        )
        assert comp.archetype_primary == "poke"
        assert comp.ranged_count == 5

    def test_enchanters_classify_peel(self):
        comp = profile_team(
            tuple(f"E{i}" for i in range(5)),
            {f"E{i}": enchanter(f"E{i}") for i in range(5)},
        )
        assert comp.archetype_primary == "peel"

    def test_damage_warning_at_four_same_type(self):
        profiles = {f"P{i}": artillery(f"P{i}") for i in range(4)}
        profiles["T"] = tank("T")  # physical
        comp = profile_team(("P0", "P1", "P2", "P3", "T"), profiles)
        assert comp.damage_mix == {"physical": 1, "magic": 4, "mixed": 0}
        assert comp.damage_warning == "mostly_magic"

    def test_mixed_damage_no_warning(self):
        profiles = {
            "A": artillery("A"),
            "B": artillery("B"),
            "C": tank("C"),
            "D": tank("D"),
            "E": enchanter("E"),
        }
        comp = profile_team(("A", "B", "C", "D", "E"), profiles)
        assert comp.damage_warning is None

    def test_missing_profile_marks_partial_and_normalizes(self):
        profiles = {f"T{i}": tank(f"T{i}") for i in range(4)}  # 5th unknown
        comp = profile_team(("T0", "T1", "T2", "T3", "Nueve"), profiles)
        assert comp.partial is True
        # Normalized over the 4 with data, so still a clear engage comp.
        assert comp.archetype_primary == "engage"
        assert comp.breakdown[4]["missing"] is True


class TestCounterTriangle:
    def test_triangle(self):
        assert archetype_counter_bonus("engage", "poke") == 1
        assert archetype_counter_bonus("poke", "peel") == 1
        assert archetype_counter_bonus("peel", "engage") == 1
        assert archetype_counter_bonus("poke", "engage") == -1
        assert archetype_counter_bonus("engage", "engage") == 0
        assert archetype_counter_bonus("flexible", "poke") == 0
