"""Tests for cardio.net.network_strategy — RemoteStrategy.

RemoteStrategy.fetch_remote_cards() is the one method that touches the network.  All
tests that exercise it use a real loopback socket pair so we test the actual framing
and JSON decode path, not just a mock.

RemoteStrategy.cards_to_be_played() is tested both after a real network exchange and
directly (by populating _pending manually) to isolate the data-transformation logic
from the network layer.

ConnectionError propagation is tested by closing the remote socket while
fetch_remote_cards is blocked, which reproduces the mid-fight disconnection scenario
that NetworkFightVnC catches and converts to PeerDisconnectedError.
"""

import socket
import threading
import pytest

from cardio import Grid, GridPos, FightCard, FightVnC
from cardio.card import Card
from cardio import skills
from cardio.net.network_strategy import RemoteStrategy
from cardio.net.protocol import send_message, make_fight_cards_msg, serialise_card_placement



# ── fixtures ───────────────────────────────────────────────────────────────────


def _make_card(name="Cat", power=1, health=2, skill_types=None):
    return Card(
        name=name,
        power=power,
        health=health,
        costs_fire=0,
        costs_spirits=1,
        has_fire=1,
        has_spirits=1,
        skills=skill_types or [],
    )


def _loopback_pair():
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("127.0.0.1", 0))
    srv.listen(1)
    port = srv.getsockname()[1]
    cli = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    cli.connect(("127.0.0.1", port))
    conn, _ = srv.accept()
    srv.close()
    return cli, conn


@pytest.fixture
def grid():
    return Grid(4)


@pytest.fixture
def initialized_fight(grid):
    """Initialize FightCard class-level fight state with a real VnC and grid."""
    vnc = FightVnC(grid=grid, computerstrategy=None, humanplayer=None)
    FightCard.init_fight(vnc, grid)
    return vnc, grid


# ── RemoteStrategy construction ────────────────────────────────────────────────


class TestRemoteStrategyConstruction:
    def test_inherits_computer_strategy(self):
        from cardio.computer_strategies import ComputerStrategy
        cli, srv = _loopback_pair()
        g = Grid(4)
        strat = RemoteStrategy(sock=cli, grid=g)
        assert isinstance(strat, ComputerStrategy)
        cli.close()
        srv.close()

    def test_pending_starts_empty(self):
        cli, srv = _loopback_pair()
        g = Grid(4)
        strat = RemoteStrategy(sock=cli, grid=g)
        assert strat._pending == []
        cli.close()
        srv.close()


# ── fetch_remote_cards ─────────────────────────────────────────────────────────


class TestFetchRemoteCards:
    def _send_fight_cards(self, sock, placements):
        """Send a FIGHT_CARDS message containing *placements* over *sock*."""
        msg = make_fight_cards_msg(placements)
        send_message(sock, msg)

    def test_fetch_populates_pending_with_one_card(self, initialized_fight):
        _, grid = initialized_fight
        cli, srv = _loopback_pair()
        strat = RemoteStrategy(sock=srv, grid=grid)

        card = _make_card("Fox", power=2, health=3)
        payload = [serialise_card_placement(0, card)]

        t = threading.Thread(
            target=self._send_fight_cards, args=(cli, payload), daemon=True
        )
        t.start()
        strat.fetch_remote_cards()
        t.join(timeout=2)

        assert len(strat._pending) == 1
        pos, fc = strat._pending[0]
        assert pos == GridPos(1, 0)  # Line 1 (active line), slot 0.
        assert fc.name == "Fox"
        cli.close()
        srv.close()

    def test_fetch_maps_to_line_1_not_line_0(self, initialized_fight):
        """All received cards must land in line 1, skipping the prep line."""
        _, grid = initialized_fight
        cli, srv = _loopback_pair()
        strat = RemoteStrategy(sock=srv, grid=grid)

        card = _make_card("Deer")
        payload = [serialise_card_placement(2, card)]

        t = threading.Thread(
            target=self._send_fight_cards, args=(cli, payload), daemon=True
        )
        t.start()
        strat.fetch_remote_cards()
        t.join(timeout=2)

        pos, _ = strat._pending[0]
        assert pos.line == 1  # Active computer line, not prep line 0.
        cli.close()
        srv.close()

    def test_fetch_multiple_cards(self, initialized_fight):
        _, grid = initialized_fight
        cli, srv = _loopback_pair()
        strat = RemoteStrategy(sock=srv, grid=grid)

        cards = [_make_card(f"Card{i}") for i in range(3)]
        payload = [serialise_card_placement(i, c) for i, c in enumerate(cards)]

        t = threading.Thread(
            target=self._send_fight_cards, args=(cli, payload), daemon=True
        )
        t.start()
        strat.fetch_remote_cards()
        t.join(timeout=2)

        assert len(strat._pending) == 3
        slots = [pos.slot for pos, _ in strat._pending]
        assert sorted(slots) == [0, 1, 2]
        cli.close()
        srv.close()

    def test_fetch_empty_cards_list(self, initialized_fight):
        """A round where the opponent plays no cards must result in empty _pending."""
        _, grid = initialized_fight
        cli, srv = _loopback_pair()
        strat = RemoteStrategy(sock=srv, grid=grid)

        t = threading.Thread(
            target=self._send_fight_cards, args=(cli, []), daemon=True
        )
        t.start()
        strat.fetch_remote_cards()
        t.join(timeout=2)

        assert strat._pending == []
        cli.close()
        srv.close()

    def test_fetch_preserves_skills(self, initialized_fight):
        """Skills on received cards must survive the wire round-trip."""
        _, grid = initialized_fight
        cli, srv = _loopback_pair()
        strat = RemoteStrategy(sock=srv, grid=grid)

        card = _make_card("Porcupine", skill_types=[skills.Spines])
        payload = [serialise_card_placement(1, card)]

        t = threading.Thread(
            target=self._send_fight_cards, args=(cli, payload), daemon=True
        )
        t.start()
        strat.fetch_remote_cards()
        t.join(timeout=2)

        _, fc = strat._pending[0]
        assert skills.Spines in fc.skills
        cli.close()
        srv.close()

    def test_unexpected_message_type_results_in_empty_pending(self, initialized_fight):
        """A message that is not FIGHT_CARDS must not crash and must leave _pending empty."""
        _, grid = initialized_fight
        cli, srv = _loopback_pair()
        strat = RemoteStrategy(sock=srv, grid=grid)

        def _send_wrong():
            from cardio.net.protocol import send_message
            send_message(cli, {"type": "SOME_OTHER_MSG"})

        t = threading.Thread(target=_send_wrong, daemon=True)
        t.start()
        strat.fetch_remote_cards()
        t.join(timeout=2)

        assert strat._pending == []
        cli.close()
        srv.close()

    def test_fetch_raises_connection_error_when_remote_closes(self, initialized_fight):
        """Closing the remote socket while blocked in recv must raise ConnectionError.

        This is the raw protocol-level signal that NetworkFightVnC then converts into
        PeerDisconnectedError so play.py can handle it cleanly.
        """
        _, grid = initialized_fight
        cli, srv = _loopback_pair()
        strat = RemoteStrategy(sock=srv, grid=grid)

        # Close the sending side without sending anything — simulates a peer crash.
        def _disconnect():
            cli.close()

        t = threading.Thread(target=_disconnect, daemon=True)
        t.start()

        with pytest.raises(ConnectionError):
            strat.fetch_remote_cards()

        t.join(timeout=2)
        srv.close()



# ── cards_to_be_played ─────────────────────────────────────────────────────────


class TestCardsToBePlayedClearsPending:
    def test_returns_pending_list(self, initialized_fight):
        _, grid = initialized_fight
        cli, srv = _loopback_pair()
        strat = RemoteStrategy(sock=cli, grid=grid)

        # Populate _pending directly without touching the network.
        card = _make_card("TestCard")
        fc = FightCard.from_card(card)
        expected = [GridPos(1, 0), fc]
        strat._pending = [expected]

        result = strat.cards_to_be_played(round_number=0)
        assert result == [expected]
        cli.close()
        srv.close()

    def test_pending_is_cleared_after_call(self, initialized_fight):
        _, grid = initialized_fight
        cli, srv = _loopback_pair()
        strat = RemoteStrategy(sock=cli, grid=grid)

        card = _make_card("Deer")
        fc = FightCard.from_card(card)
        strat._pending = [(GridPos(1, 1), fc)]

        strat.cards_to_be_played(round_number=0)
        assert strat._pending == []
        cli.close()
        srv.close()

    def test_consecutive_calls_return_separate_pending_batches(self, initialized_fight):
        """Two calls in successive rounds must each return only their own batch."""
        _, grid = initialized_fight
        cli, srv = _loopback_pair()
        strat = RemoteStrategy(sock=cli, grid=grid)

        fc1 = FightCard.from_card(_make_card("A"))
        fc2 = FightCard.from_card(_make_card("B"))

        strat._pending = [(GridPos(1, 0), fc1)]
        r1 = strat.cards_to_be_played(0)
        assert len(r1) == 1

        strat._pending = [(GridPos(1, 1), fc2)]
        r2 = strat.cards_to_be_played(1)
        assert len(r2) == 1
        assert r1[0][1].name == "A"
        assert r2[0][1].name == "B"
        cli.close()
        srv.close()

    def test_empty_pending_returns_empty_list(self, initialized_fight):
        _, grid = initialized_fight
        cli, srv = _loopback_pair()
        strat = RemoteStrategy(sock=cli, grid=grid)
        assert strat.cards_to_be_played(0) == []
        cli.close()
        srv.close()
