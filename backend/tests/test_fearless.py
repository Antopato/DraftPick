import random

import pytest

from app.draft.engine import ChampionUnavailableError, DraftEngine, DraftStatus
from app.draft.sequence import DRAFT_SEQUENCE, TOTAL_TURNS, Team

from .conftest import POOL, play_turns

B, R = Team.BLUE, Team.RED


def _start(engine: DraftEngine) -> DraftEngine:
    engine.set_ready(B)
    engine.set_ready(R)
    return engine


def _play_full_game(fearless_blocked: set[str]) -> DraftEngine:
    engine = _start(
        DraftEngine(champion_pool=set(POOL), fearless_blocked=fearless_blocked)
    )
    play_turns(engine, TOTAL_TURNS)
    assert engine.status == DraftStatus.COMPLETED
    return engine


class TestFearless:
    def test_blocked_champion_cannot_be_picked_by_either_team(self):
        engine = _start(
            DraftEngine(champion_pool=set(POOL), fearless_blocked={"Champ10"})
        )
        play_turns(engine, 6)  # -> blue pick 1
        with pytest.raises(ChampionUnavailableError):
            engine.confirm(B, "Champ10")
        play_turns(engine, 1)  # -> red pick 1
        with pytest.raises(ChampionUnavailableError):
            engine.confirm(R, "Champ10")

    def test_blocked_champion_cannot_be_banned_nor_hovered(self):
        engine = _start(
            DraftEngine(champion_pool=set(POOL), fearless_blocked={"Champ10"})
        )
        with pytest.raises(ChampionUnavailableError):
            engine.confirm(B, "Champ10")  # blue ban 1
        with pytest.raises(ChampionUnavailableError):
            engine.hover(B, "Champ10")

    def test_series_carries_picks_but_not_bans(self):
        """Fearless blocks PICKS from previous games, never their bans."""
        game1 = _play_full_game(set())
        picks_g1 = set(game1.picks[B]) | set(game1.picks[R])
        bans_g1 = {c for c in game1.bans[B] + game1.bans[R] if c is not None}

        # This mirrors RoomManager._next_game: only picks carry over.
        game2 = _start(
            DraftEngine(champion_pool=set(POOL), fearless_blocked=picks_g1)
        )
        for champion in picks_g1:
            with pytest.raises(ChampionUnavailableError):
                engine_team, _ = DRAFT_SEQUENCE[game2.turn_index]
                game2.confirm(engine_team, champion)
        # A champion merely banned in game 1 is free again in game 2.
        free_ban = sorted(bans_g1 - picks_g1)[0]
        team, _ = DRAFT_SEQUENCE[game2.turn_index]
        game2.confirm(team, free_ban)

    def test_two_game_series_accumulates_blocks(self):
        game1 = _play_full_game(set())
        blocked_after_g1 = set(game1.picks[B]) | set(game1.picks[R])
        game2 = _play_full_game(blocked_after_g1)
        blocked_after_g2 = (
            blocked_after_g1 | set(game2.picks[B]) | set(game2.picks[R])
        )
        assert len(blocked_after_g2) == 20  # 10 picks per game, no overlap
        game3 = _start(
            DraftEngine(champion_pool=set(POOL), fearless_blocked=blocked_after_g2)
        )
        assert game3.selectable() == set(POOL) - blocked_after_g2

    def test_random_timeout_pick_never_selects_blocked(self):
        blocked = {f"Champ{i:02d}" for i in range(35)}  # most of the pool blocked
        engine = _start(
            DraftEngine(
                champion_pool=set(POOL),
                fearless_blocked=blocked,
                rng=random.Random(7),
            )
        )
        play_turns(engine, 6)  # -> blue pick 1
        for _ in range(10):  # all remaining turns resolved by timeout
            if engine.status != DraftStatus.IN_PROGRESS:
                break
            result = engine.resolve_timeout()
            if result.champion_id is not None:
                assert result.champion_id not in blocked
