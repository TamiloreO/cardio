import pytest
from cardio import HumanPlayer
from cardio.run_stats import RunStats, RunHistory


class TestHumanPlayerInit:
    def test_basic_attributes(self):
        p = HumanPlayer("Human")
        assert p.name == "Human"
        assert p.lives == 2
        assert p.gems == 0
        assert p.spirits == 3
        assert p.deck.name == "main"
        assert p.collection.name == "collection"
        assert p.hamster_blueprint.name == "Hamster"

    def test_run_history_initialized(self):
        p = HumanPlayer("Human")
        assert isinstance(p.run_history, RunHistory)
        assert p.run_history.total_runs() == 0

    def test_current_run_stats_none_initially(self):
        p = HumanPlayer("Human")
        assert p.current_run_stats is None


class TestHumanPlayerCreateNew:
    def test_creates_player_with_collection(self):
        p = HumanPlayer.create_new("Human")
        assert p.name == "Human"
        assert len(p.collection.cards) > 0

    def test_new_player_has_empty_run_history(self):
        p = HumanPlayer.create_new("Human")
        assert p.run_history.total_runs() == 0


class TestHumanPlayerRunTracking:
    def test_start_run_creates_stats(self):
        p = HumanPlayer("TestPlayer")
        stats = p.start_run("seed123")
        assert stats is not None
        assert stats.base_seed == "seed123"
        assert p.current_run_stats is stats

    def test_start_run_empty_seed_raises(self):
        p = HumanPlayer("TestPlayer")
        with pytest.raises(ValueError, match="base_seed cannot be empty"):
            p.start_run("")

    def test_end_run_adds_to_history(self):
        p = HumanPlayer("TestPlayer")
        p.start_run("seed123")
        completed = p.end_run(final_rung=5)
        assert completed is not None
        assert completed.final_rung == 5
        assert p.run_history.total_runs() == 1
        assert p.current_run_stats is None

    def test_end_run_negative_rung_raises(self):
        p = HumanPlayer("TestPlayer")
        p.start_run("seed123")
        with pytest.raises(ValueError, match="final_rung cannot be negative"):
            p.end_run(final_rung=-1)

    def test_end_run_without_start_returns_none(self):
        p = HumanPlayer("TestPlayer")
        assert p.end_run(final_rung=5) is None
        assert p.run_history.total_runs() == 0

    def test_multiple_runs_accumulate_in_history(self):
        p = HumanPlayer("TestPlayer")

        p.start_run("seed1")
        p.end_run(final_rung=3)

        p.start_run("seed2")
        p.end_run(final_rung=7)

        p.start_run("seed3")
        p.end_run(final_rung=5)

        assert p.run_history.total_runs() == 3
        assert p.run_history.best_rung() == 7

    def test_start_new_run_replaces_current(self):
        p = HumanPlayer("TestPlayer")
        p.start_run("seed1")
        p.start_run("seed2")
        assert p.current_run_stats.base_seed == "seed2"

    def test_run_stats_tracking_during_run(self):
        p = HumanPlayer("TestPlayer")
        stats = p.start_run("seed123")

        stats.record_fight_won()
        stats.record_fight_won()
        stats.record_fight_lost()
        stats.record_card_collected(3)

        completed = p.end_run(final_rung=10)
        assert completed.fights_won == 2
        assert completed.fights_lost == 1
        assert completed.cards_collected == 3
        assert completed.ended_at is not None
