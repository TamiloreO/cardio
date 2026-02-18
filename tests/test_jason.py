import cardio.jason as jason
from cardio import HumanPlayer
from cardio.blueprints import thecatalog
from cardio.run import Run
from cardio.run_stats import RunStats, RunHistory
from cardio.blueprints import Blueprint


def test_encode_decode_humanplayer_inluding_cards_etc():
    c = thecatalog.get("Church Mouse").instantiate()
    hp = HumanPlayer("me")
    hp.deck.add_card(c)
    hp.collection.add_card(c)
    j = jason.encode(hp)
    np = jason.decode(j)
    assert isinstance(np, HumanPlayer)
    assert np.name == hp.name
    assert np.lives == hp.lives
    assert np.gems == hp.gems
    assert np.spirits == hp.spirits
    assert np.deck.size() == hp.deck.size()
    assert np.collection.size() == hp.collection.size()
    assert np.deck.cards[0].name == hp.deck.cards[0].name
    assert np.collection.cards[0].name == hp.collection.cards[0].name


def test_encode_decode_run():
    r = Run()
    j = jason.encode(r)
    nr = jason.decode(j)
    assert isinstance(nr, Run)
    assert nr.base_seed == r.base_seed
    assert nr.current_rung == r.current_rung
    assert nr.current_index == r.current_index


def test_encode_decode_blueprint():
    b = thecatalog._blueprints[-1]
    j = jason.encode(b)
    nb = jason.decode(j)
    assert isinstance(nb, Blueprint)
    assert nb.is_gameplay_equal(b)
    assert nb.name == b.name


def test_encode_decode_run_stats():
    stats = RunStats(rungs_completed=7, seed="test_seed_123")
    j = jason.encode(stats)
    ns = jason.decode(j)
    assert isinstance(ns, RunStats)
    assert ns.rungs_completed == stats.rungs_completed
    assert ns.seed == stats.seed
    assert ns.timestamp == stats.timestamp


def test_encode_decode_run_history():
    history = RunHistory()
    history.add_run(RunStats(rungs_completed=5, seed="seed1"))
    history.add_run(RunStats(rungs_completed=10, seed="seed2"))

    j = jason.encode(history)
    nh = jason.decode(j)
    assert isinstance(nh, RunHistory)
    assert nh.total_runs() == 2
    assert nh.runs[0].rungs_completed == 5
    assert nh.runs[1].rungs_completed == 10


def test_encode_decode_humanplayer_with_run_history():
    hp = HumanPlayer("me")
    hp.add_run_to_history(rungs_completed=3, seed="seed_a")
    hp.add_run_to_history(rungs_completed=8, seed="seed_b")

    j = jason.encode(hp)
    np = jason.decode(j)

    assert isinstance(np, HumanPlayer)
    assert isinstance(np.run_history, RunHistory)
    assert np.run_history.total_runs() == 2
    assert np.run_history.best_run().rungs_completed == 8
