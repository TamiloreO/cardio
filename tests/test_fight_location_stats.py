"""Tests for fight location integration with run stats."""

import pytest
from unittest.mock import MagicMock, patch
from cardio import HumanPlayer, Grid
from cardio.locations.fight_location import FightLocation
from cardio.computer_strategies import SimpleRungBasedStrategy


class MockFightView:
    """Mock fight view for testing."""

    def __init__(self, *args, **kwargs):
        self.fight_handled = False

    def handle_fight(self):
        self.fight_handled = True

    def close(self):
        pass


class TestFightLocationStatsTracking:
    def test_fight_won_records_stat(self):
        player = HumanPlayer("TestPlayer")
        player.start_run("test_seed")
        player.lives = 2

        location = FightLocation("seed", 1, 0, [0])

        with patch.object(MockFightView, "handle_fight"):
            result = location.handle(MockFightView, player)

        assert result is True
        assert player.current_run_stats.fights_won == 1
        assert player.current_run_stats.fights_lost == 0

    def test_fight_lost_records_stat(self):
        player = HumanPlayer("TestPlayer")
        player.start_run("test_seed")
        player.lives = 2

        location = FightLocation("seed", 1, 0, [0])

        def lose_fight(self):
            player.lives -= 1

        with patch.object(MockFightView, "handle_fight", lose_fight):
            result = location.handle(MockFightView, player)

        assert result is True
        assert player.current_run_stats.fights_won == 0
        assert player.current_run_stats.fights_lost == 1

    def test_fight_lost_all_lives_records_stat(self):
        player = HumanPlayer("TestPlayer")
        player.start_run("test_seed")
        player.lives = 1

        location = FightLocation("seed", 1, 0, [0])

        def lose_fight(self):
            player.lives -= 1

        with patch.object(MockFightView, "handle_fight", lose_fight):
            result = location.handle(MockFightView, player)

        assert result is False
        assert player.current_run_stats.fights_won == 0
        assert player.current_run_stats.fights_lost == 1

    def test_multiple_fights_accumulate_stats(self):
        player = HumanPlayer("TestPlayer")
        player.start_run("test_seed")
        player.lives = 5

        location = FightLocation("seed", 1, 0, [0])

        with patch.object(MockFightView, "handle_fight"):
            location.handle(MockFightView, player)
            location.handle(MockFightView, player)

        def lose_fight(self):
            player.lives -= 1

        with patch.object(MockFightView, "handle_fight", lose_fight):
            location.handle(MockFightView, player)

        assert player.current_run_stats.fights_won == 2
        assert player.current_run_stats.fights_lost == 1

    def test_no_stats_recorded_when_no_active_run(self):
        player = HumanPlayer("TestPlayer")
        player.lives = 2
        assert player.current_run_stats is None

        location = FightLocation("seed", 1, 0, [0])

        with patch.object(MockFightView, "handle_fight"):
            result = location.handle(MockFightView, player)

        assert result is True
        assert player.current_run_stats is None
