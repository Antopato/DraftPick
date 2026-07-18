import random

import pytest

from app.draft.engine import (
    ChampionUnavailableError,
    DraftEngine,
    DraftStatus,
    InvalidActionError,
    NotYourTurnError,
)
from app.draft.sequence import DRAFT_SEQUENCE, TOTAL_TURNS, ActionType, Team, slot_number

from .conftest import POOL, play_turns

B, R = Team.BLUE, Team.RED
BAN, PICK = ActionType.BAN, ActionType.PICK


class TestSequence:
    def test_exact_tournament_sequence(self):
        assert DRAFT_SEQUENCE == (
            # Ban phase 1: B R B R B R
            (B, BAN), (R, BAN), (B, BAN), (R, BAN), (B, BAN), (R, BAN),
            # Pick phase 1: B1, R1, R2, B2, B3, R3
            (B, PICK), (R, PICK), (R, PICK), (B, PICK), (B, PICK), (R, PICK),
            # Ban phase 2: R B R B
            (R, BAN), (B, BAN), (R, BAN), (B, BAN),
            # Pick phase 2: R4, B4, B5, R5
            (R, PICK), (B, PICK), (B, PICK), (R, PICK),
        )
        assert TOTAL_TURNS == 20

    def test_slot_numbers(self):
        assert slot_number(0) == 1  # blue ban 1
        assert slot_number(5) == 3  # red ban 3
        assert slot_number(6) == 1  # blue pick 1
        assert slot_number(12) == 4  # red ban 4
        assert slot_number(19) == 5  # red pick 5

    def test_full_draft_completes(self, engine):
        play_turns(engine, TOTAL_TURNS)
        assert engine.status == DraftStatus.COMPLETED
        assert len(engine.bans[B]) == 5
        assert len(engine.bans[R]) == 5
        assert len(engine.picks[B]) == 5
        assert len(engine.picks[R]) == 5
        # No champion appears twice across bans and picks.
        all_used = (
            engine.bans[B] + engine.bans[R] + engine.picks[B] + engine.picks[R]
        )
        assert len(all_used) == len(set(all_used)) == 20

    def test_no_actions_after_completion(self, engine):
        play_turns(engine, TOTAL_TURNS)
        with pytest.raises(InvalidActionError):
            engine.confirm(B, sorted(engine.selectable())[0])


class TestReadyCheck:
    def test_draft_starts_only_when_both_ready(self):
        e = DraftEngine(champion_pool=set(POOL))
        assert e.status == DraftStatus.WAITING
        assert e.set_ready(Team.BLUE) is False
        assert e.status == DraftStatus.WAITING
        assert e.set_ready(Team.RED) is True
        assert e.status == DraftStatus.IN_PROGRESS

    def test_actions_rejected_before_start(self):
        e = DraftEngine(champion_pool=set(POOL))
        with pytest.raises(InvalidActionError):
            e.confirm(Team.BLUE, "Champ00")
        with pytest.raises(InvalidActionError):
            e.hover(Team.BLUE, "Champ00")


class TestTurnOwnership:
    def test_red_cannot_act_on_blue_turn(self, engine):
        with pytest.raises(NotYourTurnError):
            engine.confirm(R, "Champ00")
        with pytest.raises(NotYourTurnError):
            engine.hover(R, "Champ00")

    def test_turns_alternate_per_sequence(self, engine):
        for expected_team, _ in DRAFT_SEQUENCE:
            other = R if expected_team == B else B
            with pytest.raises(NotYourTurnError):
                engine.confirm(other, sorted(engine.selectable())[0])
            engine.confirm(expected_team, sorted(engine.selectable())[0])
        assert engine.status == DraftStatus.COMPLETED


class TestChampionLegality:
    def test_banned_champion_cannot_be_picked(self, engine):
        engine.confirm(B, "Champ00")  # blue ban 1
        play_turns(engine, 5)  # finish ban phase 1 -> blue pick 1
        with pytest.raises(ChampionUnavailableError):
            engine.confirm(B, "Champ00")

    def test_picked_champion_cannot_be_repicked_or_banned(self, engine):
        play_turns(engine, 6)  # ban phase 1 done
        engine.confirm(B, "Champ50")  # blue pick 1
        with pytest.raises(ChampionUnavailableError):
            engine.confirm(R, "Champ50")  # red pick 1
        play_turns(engine, 5)  # rest of pick phase 1 -> red ban 4 (turn 12)
        with pytest.raises(ChampionUnavailableError):
            engine.confirm(R, "Champ50")

    def test_unknown_champion_rejected(self, engine):
        with pytest.raises(ChampionUnavailableError):
            engine.confirm(B, "NotAChampion")

    def test_hover_unavailable_champion_rejected(self, engine):
        engine.confirm(B, "Champ00")
        with pytest.raises(ChampionUnavailableError):
            engine.hover(R, "Champ00")


class TestHover:
    def test_hover_set_and_cleared_on_confirm(self, engine):
        engine.hover(B, "Champ01")
        assert engine.hovered == "Champ01"
        engine.confirm(B, "Champ01")
        assert engine.hovered is None

    def test_hover_can_be_cleared(self, engine):
        engine.hover(B, "Champ01")
        engine.hover(B, None)
        assert engine.hovered is None


class TestTimeout:
    def test_timeout_confirms_hovered(self, engine):
        engine.hover(B, "Champ07")
        result = engine.resolve_timeout()
        assert result.champion_id == "Champ07"
        assert result.is_auto is True
        assert engine.bans[B] == ["Champ07"]
        assert engine.turn_index == 1

    def test_timeout_without_hover_skips_ban(self, engine):
        result = engine.resolve_timeout()
        assert result.action_type == BAN
        assert result.champion_id is None
        assert engine.bans[B] == [None]
        assert engine.turn_index == 1

    def test_skipped_ban_does_not_consume_a_champion(self, engine):
        engine.resolve_timeout()
        assert engine.selectable() == set(POOL)

    def test_timeout_without_hover_picks_random_available(self, engine):
        play_turns(engine, 6)  # -> blue pick 1
        used = set(engine.unavailable())
        result = engine.resolve_timeout()
        assert result.action_type == PICK
        assert result.is_auto is True
        assert result.champion_id in POOL
        assert result.champion_id not in used

    def test_timeout_rejected_when_not_in_progress(self):
        e = DraftEngine(champion_pool=set(POOL))
        with pytest.raises(InvalidActionError):
            e.resolve_timeout()


class TestReplay:
    def test_replay_reproduces_state(self, engine):
        results = []
        engine2 = DraftEngine(champion_pool=set(POOL), rng=random.Random(1))
        # Play 13 turns (into ban phase 2), capturing TurnResults.
        for _ in range(13):
            team, _ = DRAFT_SEQUENCE[engine.turn_index]
            champion = sorted(engine.selectable())[-1]
            results.append(engine.confirm(team, champion))
        engine2.replay(results)
        assert engine2.turn_index == engine.turn_index
        assert engine2.bans == engine.bans
        assert engine2.picks == engine.picks
        assert engine2.status == DraftStatus.IN_PROGRESS

    def test_replay_with_skipped_ban(self, engine):
        results = [engine.resolve_timeout()]  # skipped blue ban 1
        engine2 = DraftEngine(champion_pool=set(POOL))
        engine2.replay(results)
        assert engine2.bans[B] == [None]
        assert engine2.turn_index == 1
