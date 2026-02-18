import cardio.jason as jason
from cardio import HumanPlayer
from cardio.blueprints import thecatalog
from cardio.run import Run
from cardio.blueprints import Blueprint
from cardio.run_stats import RunStats, RunHistory


class TestEncodeDecodeHumanPlayer:
    def test_basic_player_with_cards(self):
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

    def test_player_with_run_history(self):
        hp = HumanPlayer("player_with_history")
        hp.start_run("seed1")
        hp.current_run_stats.record_fight_won()
        hp.end_run(final_rung=5)

        hp.start_run("seed2")
        hp.current_run_stats.record_fight_won()
        hp.current_run_stats.record_fight_lost()
        hp.end_run(final_rung=10)

        j = jason.encode(hp)
        np = jason.decode(j)

        assert isinstance(np, HumanPlayer)
        assert isinstance(np.run_history, RunHistory)
        assert np.run_history.total_runs() == 2
        assert np.run_history.best_rung() == 10
        assert np.run_history.total_fights_won() == 2
        assert np.run_history.total_fights_lost() == 1

    def test_player_with_empty_run_history(self):
        hp = HumanPlayer("new_player")
        j = jason.encode(hp)
        np = jason.decode(j)

        assert isinstance(np, HumanPlayer)
        assert isinstance(np.run_history, RunHistory)
        assert np.run_history.total_runs() == 0


class TestEncodeDecodeRun:
    def test_basic_run(self):
        r = Run()
        j = jason.encode(r)
        nr = jason.decode(j)
        assert isinstance(nr, Run)
        assert nr.base_seed == r.base_seed
        assert nr.current_rung == r.current_rung
        assert nr.current_index == r.current_index


class TestEncodeDecodeBlueprint:
    def test_blueprint_roundtrip(self):
        b = thecatalog._blueprints[-1]
        j = jason.encode(b)
        nb = jason.decode(j)
        assert isinstance(nb, Blueprint)
        assert nb.is_gameplay_equal(b)
        assert nb.name == b.name


class TestEncodeDecodeRunStats:
    def test_basic_run_stats(self):
        stats = RunStats(
            base_seed="test_seed",
            final_rung=15,
            fights_won=8,
            fights_lost=3,
            cards_collected=12,
        )
        stats.complete()
        j = jason.encode(stats)
        ns = jason.decode(j)

        assert isinstance(ns, RunStats)
        assert ns.base_seed == stats.base_seed
        assert ns.final_rung == stats.final_rung
        assert ns.fights_won == stats.fights_won
        assert ns.fights_lost == stats.fights_lost
        assert ns.cards_collected == stats.cards_collected
        assert ns.ended_at == stats.ended_at


class TestEncodeDecodeRunHistory:
    def test_run_history_with_multiple_runs(self):
        history = RunHistory()
        history.add_run(RunStats(base_seed="s1", final_rung=5, fights_won=2))
        history.add_run(RunStats(base_seed="s2", final_rung=10, fights_lost=1))
        history.add_run(RunStats(base_seed="s3", final_rung=7, cards_collected=5))

        j = jason.encode(history)
        nh = jason.decode(j)

        assert isinstance(nh, RunHistory)
        assert nh.total_runs() == 3
        assert nh.best_rung() == 10
        assert nh.total_fights_won() == 2
        assert nh.total_fights_lost() == 1

    def test_empty_run_history(self):
        history = RunHistory()
        j = jason.encode(history)
        nh = jason.decode(j)

        assert isinstance(nh, RunHistory)
        assert nh.total_runs() == 0
