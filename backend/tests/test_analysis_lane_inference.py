from app.analysis.lane_inference import infer_lanes
from tests.conftest import make_profile

TEAM = ("Aatrox", "LeeSin", "Ahri", "Jinx", "Thresh")
PROFILES = {
    "Aatrox": make_profile("Aatrox", lanes=("top",)),
    "LeeSin": make_profile("LeeSin", lanes=("jungle",)),
    "Ahri": make_profile("Ahri", lanes=("mid",)),
    "Jinx": make_profile("Jinx", lanes=("bot",)),
    "Thresh": make_profile("Thresh", lanes=("support",)),
}


class TestInference:
    def test_fully_assigned_passthrough(self):
        assigned = ("top", "jungle", "mid", "bot", "support")
        lanes, inferred = infer_lanes(TEAM, assigned, PROFILES)
        assert lanes == list(assigned)
        assert inferred is False

    def test_single_hole_filled_by_elimination(self):
        assigned = ("top", "jungle", None, "bot", "support")
        lanes, inferred = infer_lanes(TEAM, assigned, PROFILES)
        assert lanes[2] == "mid"
        assert inferred is True

    def test_fully_unassigned_solved_from_positions(self):
        lanes, inferred = infer_lanes(TEAM, (None,) * 5, PROFILES)
        assert lanes == ["top", "jungle", "mid", "bot", "support"]
        assert inferred is True

    def test_unknown_champion_gets_leftover_lane(self):
        profiles = dict(PROFILES)
        del profiles["Ahri"]
        lanes, inferred = infer_lanes(TEAM, (None,) * 5, profiles)
        assert lanes[2] == "mid"  # only lane left once the others are forced
        assert inferred is True

    def test_flex_pick_resolved_by_position_priority(self):
        # Two champions both listing mid; primary position wins the tie.
        profiles = {
            "A": make_profile("A", lanes=("mid", "top")),
            "B": make_profile("B", lanes=("mid",)),
            "C": make_profile("C", lanes=("jungle",)),
            "D": make_profile("D", lanes=("bot",)),
            "E": make_profile("E", lanes=("support",)),
        }
        lanes, _ = infer_lanes(("A", "B", "C", "D", "E"), (None,) * 5, profiles)
        assert lanes == ["top", "mid", "jungle", "bot", "support"]

    def test_deterministic(self):
        results = {
            tuple(infer_lanes(TEAM, (None,) * 5, PROFILES)[0]) for _ in range(5)
        }
        assert len(results) == 1
