"""Tests for RunStatsWidget data requirements.

These tests verify that player data is correctly tracked for the widget to display.
Direct widget tests are skipped due to asciimatics version incompatibilities.
"""

import pytest
from cardio import HumanPlayer


class TestRunStatsWidgetDataRequirements:
    """Tests verifying data needed by RunStatsWidget is correctly tracked."""

    def test_no_active_run_returns_none(self):
        """When there's no active run, current_run_stats should be None."""
        player = HumanPlayer("TestPlayer")
        assert player.current_run_stats is None

    def test_active_run_has_stats(self):
        """An active run should have a current_run_stats object."""
        player = HumanPlayer("TestPlayer")
        player.start_run("test_seed")
        assert player.current_run_stats is not None
        assert player.current_run_stats.base_seed == "test_seed"

    def test_fight_stats_tracked_correctly(self):
        """Verify that fight stats are tracked correctly for widget display."""
        player = HumanPlayer("TestPlayer")
        player.start_run("test_seed")

        player.current_run_stats.record_fight_won()
        player.current_run_stats.record_fight_won()
        player.current_run_stats.record_fight_lost()

        assert player.current_run_stats.fights_won == 2
        assert player.current_run_stats.fights_lost == 1

    def test_history_best_rung_available(self):
        """Verify history data is available for widget to display best rung."""
        player = HumanPlayer("TestPlayer")

        player.start_run("seed1")
        player.end_run(final_rung=5)

        player.start_run("seed2")
        player.end_run(final_rung=10)

        player.start_run("seed3")

        assert player.run_history.best_rung() == 10
        assert player.current_run_stats is not None

    def test_cards_collected_tracked(self):
        """Verify cards collected are tracked for widget display."""
        player = HumanPlayer("TestPlayer")
        player.start_run("test_seed")

        player.current_run_stats.record_card_collected(3)
        player.current_run_stats.record_card_collected(2)

        assert player.current_run_stats.cards_collected == 5

    def test_stats_cleared_after_run_ends(self):
        """Verify current stats are cleared after run ends."""
        player = HumanPlayer("TestPlayer")
        player.start_run("test_seed")
        player.current_run_stats.record_fight_won()

        player.end_run(final_rung=5)

        assert player.current_run_stats is None
        assert player.run_history.total_runs() == 1
