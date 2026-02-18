"""Tests for run statistics tracking."""

import pytest
from cardio.run_stats import RunStats, RunHistory


class TestRunStats:
    def test_creation(self):
        stats = RunStats(rungs_completed=5, seed="test_seed")
        assert stats.rungs_completed == 5
        assert stats.seed == "test_seed"
        assert stats.timestamp  # Should have a timestamp

    def test_format_summary(self):
        stats = RunStats(rungs_completed=10, seed="abcdefghij")
        summary = stats.format_summary()
        assert "10" in summary
        assert "abcdefgh" in summary  # First 8 chars of seed


class TestRunHistory:
    def test_empty_history(self):
        history = RunHistory()
        assert history.total_runs() == 0
        assert history.best_run() is None
        assert history.average_rungs() == 0.0
        assert "No runs" in history.format_summary()

    def test_add_run(self):
        history = RunHistory()
        stats = RunStats(rungs_completed=5, seed="seed1")
        history.add_run(stats)
        assert history.total_runs() == 1
        assert history.runs[0] == stats

    def test_best_run(self):
        history = RunHistory()
        history.add_run(RunStats(rungs_completed=3, seed="seed1"))
        history.add_run(RunStats(rungs_completed=7, seed="seed2"))
        history.add_run(RunStats(rungs_completed=5, seed="seed3"))

        best = history.best_run()
        assert best is not None
        assert best.rungs_completed == 7
        assert best.seed == "seed2"

    def test_average_rungs(self):
        history = RunHistory()
        history.add_run(RunStats(rungs_completed=2, seed="seed1"))
        history.add_run(RunStats(rungs_completed=4, seed="seed2"))
        history.add_run(RunStats(rungs_completed=6, seed="seed3"))

        assert history.average_rungs() == 4.0

    def test_format_summary_with_runs(self):
        history = RunHistory()
        history.add_run(RunStats(rungs_completed=5, seed="seed1"))
        history.add_run(RunStats(rungs_completed=10, seed="seed2"))

        summary = history.format_summary()
        assert "Total runs: 2" in summary
        assert "7.5" in summary  # Average
        assert "10" in summary  # Best run
