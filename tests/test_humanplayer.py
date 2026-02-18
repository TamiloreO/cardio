from cardio import HumanPlayer
from cardio.run_stats import RunHistory


def test_humanplayer_init():
    p = HumanPlayer("Human")
    assert p.name == "Human"
    assert p.lives == 2
    assert p.gems == 0
    assert p.spirits == 3
    assert p.deck.name == "main"
    assert p.collection.name == "collection"
    assert p.hamster_blueprint.name == "Hamster"
    assert isinstance(p.run_history, RunHistory)
    assert p.run_history.total_runs() == 0


def test_humanplayer_create_new():
    p = HumanPlayer.create_new("Human")
    assert p.name == "Human"
    assert len(p.collection.cards) > 0


def test_humanplayer_add_run_to_history():
    p = HumanPlayer("Human")
    assert p.run_history.total_runs() == 0

    stats = p.add_run_to_history(rungs_completed=5, seed="test_seed")
    assert p.run_history.total_runs() == 1
    assert stats.rungs_completed == 5
    assert stats.seed == "test_seed"

    # Add another run
    p.add_run_to_history(rungs_completed=10, seed="another_seed")
    assert p.run_history.total_runs() == 2
    assert p.run_history.best_run().rungs_completed == 10
