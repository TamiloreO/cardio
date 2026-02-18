from cardio import Grid, HumanPlayer
from cardio.locations.fight_location import FightLocation
from cardio.computer_strategies import SimpleRungBasedStrategy


def test_generate():
    l = FightLocation("0", 0, 0, [0])
    assert isinstance(l.grid, Grid)
    assert isinstance(l.computerstrategy, SimpleRungBasedStrategy)


class MockFightView:
    """Mock view that simulates a fight with a predetermined winner."""

    def __init__(self, winner: str, **kwargs):
        self._winner = winner

    def handle_fight(self):
        pass

    def close(self):
        pass

    @property
    def winner(self):
        return self._winner


def test_fight_records_win():
    player = HumanPlayer("Test")
    player.start_run("test_seed")
    location = FightLocation("0", 1, 0, [0])

    # Create mock that simulates human win
    mock_view_class = lambda **kwargs: MockFightView(winner="human", **kwargs)
    location.handle(mock_view_class, player)

    assert player.current_run_stats.fights_won == 1
    assert player.current_run_stats.fights_lost == 0


def test_fight_records_loss():
    player = HumanPlayer("Test")
    player.lives = 2
    player.start_run("test_seed")
    location = FightLocation("0", 1, 0, [0])

    # Create mock that simulates computer win (player loses)
    mock_view_class = lambda **kwargs: MockFightView(winner="computer", **kwargs)
    location.handle(mock_view_class, player)

    assert player.current_run_stats.fights_won == 0
    assert player.current_run_stats.fights_lost == 1


def test_fight_no_stats_if_no_active_run():
    player = HumanPlayer("Test")
    # Don't start a run - current_run_stats should be None
    assert player.current_run_stats is None

    location = FightLocation("0", 1, 0, [0])
    mock_view_class = lambda **kwargs: MockFightView(winner="human", **kwargs)

    # Should not raise even without active run stats
    location.handle(mock_view_class, player)
