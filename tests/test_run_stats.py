"""Tests for RunStats and RunHistory."""

import pytest
from datetime import datetime
from cardio.run_stats import RunStats, RunHistory


class TestRunStats:
    def test_create_with_required_fields(self):
        stats = RunStats(base_seed="test123", final_rung=5)
        assert stats.base_seed == "test123"
        assert stats.final_rung == 5
        assert stats.cards_collected == 0
        assert stats.fights_won == 0
        assert stats.fights_lost == 0
        assert stats.started_at is not None
        assert stats.ended_at is None

    def test_complete_sets_ended_at(self):
        stats = RunStats(base_seed="test123", final_rung=5)
        assert stats.ended_at is None
        stats.complete()
        assert stats.ended_at is not None
        datetime.fromisoformat(stats.ended_at)

    def test_record_fight_won(self):
        stats = RunStats(base_seed="test123", final_rung=0)
        assert stats.fights_won == 0
        stats.record_fight_won()
        assert stats.fights_won == 1
        stats.record_fight_won()
        assert stats.fights_won == 2

    def test_record_fight_lost(self):
        stats = RunStats(base_seed="test123", final_rung=0)
        assert stats.fights_lost == 0
        stats.record_fight_lost()
        assert stats.fights_lost == 1

    def test_record_card_collected(self):
        stats = RunStats(base_seed="test123", final_rung=0)
        assert stats.cards_collected == 0
        stats.record_card_collected()
        assert stats.cards_collected == 1
        stats.record_card_collected(3)
        assert stats.cards_collected == 4

    def test_record_card_collected_negative_raises(self):
        stats = RunStats(base_seed="test123", final_rung=0)
        with pytest.raises(ValueError, match="Card count cannot be negative"):
            stats.record_card_collected(-1)

    def test_get_summary(self):
        stats = RunStats(
            base_seed="abc123",
            final_rung=10,
            fights_won=5,
            fights_lost=2,
            cards_collected=8,
        )
        summary = stats.get_summary()
        assert "abc123" in summary
        assert "10" in summary
        assert "5" in summary
        assert "2" in summary
        assert "8" in summary

    def test_to_dict(self):
        stats = RunStats(
            base_seed="test",
            final_rung=7,
            fights_won=3,
            fights_lost=1,
            cards_collected=5,
        )
        d = stats.to_dict()
        assert d["base_seed"] == "test"
        assert d["final_rung"] == 7
        assert d["fights_won"] == 3
        assert d["fights_lost"] == 1
        assert d["cards_collected"] == 5
        assert "started_at" in d

    def test_from_dict(self):
        data = {
            "base_seed": "seed456",
            "final_rung": 12,
            "started_at": "2024-01-01T12:00:00",
            "ended_at": "2024-01-01T13:00:00",
            "fights_won": 6,
            "fights_lost": 2,
            "cards_collected": 10,
        }
        stats = RunStats.from_dict(data)
        assert stats.base_seed == "seed456"
        assert stats.final_rung == 12
        assert stats.started_at == "2024-01-01T12:00:00"
        assert stats.ended_at == "2024-01-01T13:00:00"
        assert stats.fights_won == 6
        assert stats.fights_lost == 2
        assert stats.cards_collected == 10

    def test_from_dict_with_missing_optional_fields(self):
        data = {"base_seed": "minimal", "final_rung": 1}
        stats = RunStats.from_dict(data)
        assert stats.base_seed == "minimal"
        assert stats.final_rung == 1
        assert stats.fights_won == 0
        assert stats.fights_lost == 0
        assert stats.cards_collected == 0

    def test_roundtrip_to_dict_from_dict(self):
        original = RunStats(
            base_seed="roundtrip",
            final_rung=15,
            fights_won=8,
            fights_lost=3,
            cards_collected=12,
        )
        original.complete()
        restored = RunStats.from_dict(original.to_dict())
        assert restored.base_seed == original.base_seed
        assert restored.final_rung == original.final_rung
        assert restored.fights_won == original.fights_won
        assert restored.fights_lost == original.fights_lost
        assert restored.cards_collected == original.cards_collected
        assert restored.ended_at == original.ended_at


class TestRunHistory:
    def test_empty_history(self):
        history = RunHistory()
        assert history.total_runs() == 0
        assert history.best_rung() == 0
        assert history.total_fights_won() == 0
        assert history.total_fights_lost() == 0

    def test_add_run(self):
        history = RunHistory()
        stats = RunStats(base_seed="run1", final_rung=5)
        history.add_run(stats)
        assert history.total_runs() == 1

    def test_add_run_none_raises(self):
        history = RunHistory()
        with pytest.raises(ValueError, match="Cannot add None"):
            history.add_run(None)

    def test_best_rung(self):
        history = RunHistory()
        history.add_run(RunStats(base_seed="r1", final_rung=5))
        history.add_run(RunStats(base_seed="r2", final_rung=10))
        history.add_run(RunStats(base_seed="r3", final_rung=3))
        assert history.best_rung() == 10

    def test_total_fights_won(self):
        history = RunHistory()
        stats1 = RunStats(base_seed="r1", final_rung=5, fights_won=3)
        stats2 = RunStats(base_seed="r2", final_rung=7, fights_won=5)
        history.add_run(stats1)
        history.add_run(stats2)
        assert history.total_fights_won() == 8

    def test_total_fights_lost(self):
        history = RunHistory()
        stats1 = RunStats(base_seed="r1", final_rung=5, fights_lost=2)
        stats2 = RunStats(base_seed="r2", final_rung=7, fights_lost=1)
        history.add_run(stats1)
        history.add_run(stats2)
        assert history.total_fights_lost() == 3

    def test_get_summary_empty(self):
        history = RunHistory()
        assert "No runs completed" in history.get_summary()

    def test_get_summary_with_runs(self):
        history = RunHistory()
        history.add_run(RunStats(base_seed="r1", final_rung=5, fights_won=3))
        history.add_run(RunStats(base_seed="r2", final_rung=10, fights_won=7))
        summary = history.get_summary()
        assert "2" in summary
        assert "10" in summary
        assert "10" in summary

    def test_to_list(self):
        history = RunHistory()
        history.add_run(RunStats(base_seed="r1", final_rung=5))
        history.add_run(RunStats(base_seed="r2", final_rung=10))
        lst = history.to_list()
        assert len(lst) == 2
        assert lst[0]["base_seed"] == "r1"
        assert lst[1]["base_seed"] == "r2"

    def test_from_list(self):
        data = [
            {"base_seed": "s1", "final_rung": 3},
            {"base_seed": "s2", "final_rung": 7},
        ]
        history = RunHistory.from_list(data)
        assert history.total_runs() == 2
        assert history.best_rung() == 7

    def test_from_list_none(self):
        history = RunHistory.from_list(None)
        assert history.total_runs() == 0

    def test_roundtrip_to_list_from_list(self):
        original = RunHistory()
        original.add_run(RunStats(base_seed="r1", final_rung=5, fights_won=2))
        original.add_run(RunStats(base_seed="r2", final_rung=8, fights_lost=1))
        restored = RunHistory.from_list(original.to_list())
        assert restored.total_runs() == original.total_runs()
        assert restored.best_rung() == original.best_rung()
        assert restored.total_fights_won() == original.total_fights_won()
        assert restored.total_fights_lost() == original.total_fights_lost()
