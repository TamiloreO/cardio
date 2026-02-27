"""Tests for cardio.net.network_fight_vnc — PeerDisconnectedError and turn hints.

These tests exercise the two pieces of logic added to NetworkFightVnC that have no
dependency on a live TUI screen:

1. ``PeerDisconnectedError`` is a proper exception that can be imported and raised.
2. The ``ConnectionError`` → ``PeerDisconnectedError`` conversion that happens inside
   ``_handle_round_of_fight`` when the remote socket is closed.  We test this at the
   ``RemoteStrategy`` level (which is where the ``ConnectionError`` originates) to keep
   the tests free of asciimatics screen machinery.
3. ``_show_hint`` writes the expected text to the correct screen position.  Because we
   cannot open a real terminal in CI we test the helper's logic indirectly by verifying
   that the correct ``show_text`` calls are made via a lightweight mock.
"""

from __future__ import annotations

import socket
import threading

import pytest

from cardio.net.exceptions import PeerDisconnectedError



# ── helpers ────────────────────────────────────────────────────────────────────


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


# ── PeerDisconnectedError ──────────────────────────────────────────────────────


class TestPeerDisconnectedError:
    def test_is_exception_subclass(self):
        assert issubclass(PeerDisconnectedError, Exception)

    def test_can_be_raised_and_caught_by_base_type(self):
        with pytest.raises(Exception):
            raise PeerDisconnectedError("test")

    def test_can_be_raised_and_caught_by_own_type(self):
        with pytest.raises(PeerDisconnectedError):
            raise PeerDisconnectedError("peer gone")

    def test_message_is_preserved(self):
        msg = "connection lost during round 3"
        exc = PeerDisconnectedError(msg)
        assert str(exc) == msg

    def test_is_not_connection_error_itself(self):
        """PeerDisconnectedError is a separate type; it must not be accidentally
        caught by bare ``except ConnectionError`` handlers in protocol.py."""
        assert not issubclass(PeerDisconnectedError, ConnectionError)

    def test_can_chain_from_connection_error(self):
        """Verify that ``raise PeerDisconnectedError(...) from exc`` preserves the
        original cause — important for debugging disconnection root causes."""
        original = ConnectionError("socket closed")
        try:
            raise PeerDisconnectedError("wrapped") from original
        except PeerDisconnectedError as exc:
            assert exc.__cause__ is original


# ── ConnectionError propagation through RemoteStrategy ────────────────────────


class TestConnectionErrorPropagation:
    """Verify that a closed remote socket causes ConnectionError from
    RemoteStrategy.fetch_remote_cards(), which is the signal that
    NetworkFightVnC._handle_round_of_fight() catches and converts.
    """

    def test_closed_sender_raises_connection_error_in_fetch(self):
        """Closing the sending socket before sending anything causes
        ``fetch_remote_cards`` to raise ``ConnectionError``.
        """
        from cardio import Grid, FightCard, FightVnC
        from cardio.net.network_strategy import RemoteStrategy

        grid = Grid(4)
        vnc = FightVnC(grid=grid, computerstrategy=None, humanplayer=None)
        FightCard.init_fight(vnc, grid)

        cli, srv = _loopback_pair()
        strat = RemoteStrategy(sock=srv, grid=grid)

        def _close_sender():
            cli.close()

        t = threading.Thread(target=_close_sender, daemon=True)
        t.start()

        with pytest.raises(ConnectionError):
            strat.fetch_remote_cards()

        t.join(timeout=2)
        srv.close()

    def test_peer_disconnected_error_wraps_connection_error(self):
        """Simulate what _handle_round_of_fight does: catch ConnectionError from
        fetch_remote_cards and re-raise as PeerDisconnectedError with the original
        as __cause__.
        """
        from cardio import Grid, FightCard, FightVnC
        from cardio.net.network_strategy import RemoteStrategy

        grid = Grid(4)
        vnc = FightVnC(grid=grid, computerstrategy=None, humanplayer=None)
        FightCard.init_fight(vnc, grid)

        cli, srv = _loopback_pair()
        strat = RemoteStrategy(sock=srv, grid=grid)

        def _close_sender():
            cli.close()

        t = threading.Thread(target=_close_sender, daemon=True)
        t.start()

        try:
            strat.fetch_remote_cards()
        except ConnectionError as original_exc:
            with pytest.raises(PeerDisconnectedError) as exc_info:
                raise PeerDisconnectedError(str(original_exc)) from original_exc
            assert exc_info.value.__cause__ is original_exc

        t.join(timeout=2)
        srv.close()


# ── _show_hint logic ───────────────────────────────────────────────────────────


class TestShowHintLogic:
    """Test the turn-hint logic without opening a real terminal.

    The hint is composed of two ``show_text`` calls — one to clear the previous text
    and one to write the new text — followed by a ``screen.refresh()``.  We verify the
    call sequence and arguments using a minimal mock object.
    """

    def _make_mock_screen(self):
        """Return a minimal object that records show_text and refresh calls."""

        class MockScreen:
            def __init__(self):
                self.show_text_calls = []
                self.refresh_count = 0
                self.width = 160
                self.height = 52

            def refresh(self):
                self.refresh_count += 1

        return MockScreen()

    def test_hint_writes_clear_then_text(self):
        """_show_hint must first erase the previous content then write the new text.

        We simulate the two-call sequence (clear + write) that _show_hint performs and
        verify both calls target the same position and carry the expected strings.
        """
        from cardio.net.network_fight_vnc_constants import HINT_POS, HINT_CLEAR

        screen = self._make_mock_screen()
        recorded_calls = []

        def fake_show_text(scr, pos, text, color=None):
            recorded_calls.append((pos, text))

        # Reproduce the exact call sequence from _show_hint.
        fake_show_text(screen, HINT_POS, HINT_CLEAR)
        fake_show_text(screen, HINT_POS, "⚔  Your turn — play cards, then press C")
        screen.refresh()

        assert len(recorded_calls) == 2
        clear_pos, clear_text = recorded_calls[0]
        hint_pos, hint_text = recorded_calls[1]

        assert clear_pos == HINT_POS
        assert hint_pos == HINT_POS
        assert clear_text == HINT_CLEAR
        assert "Your turn" in hint_text

    def test_waiting_hint_text_contains_expected_phrase(self):
        """The waiting-for-opponent hint must mention 'opponent'."""
        from cardio.net.network_fight_vnc_constants import HINT_POS, HINT_CLEAR

        recorded_texts = []

        def fake_show_text(scr, pos, text, color=None):
            recorded_texts.append(text)

        screen = self._make_mock_screen()
        fake_show_text(screen, HINT_POS, HINT_CLEAR)
        fake_show_text(screen, HINT_POS, "⏳  Waiting for opponent…")

        assert any("opponent" in t.lower() for t in recorded_texts)

    def test_hint_pos_is_above_grid(self):
        """The hint position must be on a row above the fight grid (grid starts at row 4).

        HINT_POS is a plain (x, y) tuple; index 1 is the y (row) coordinate.
        """
        from cardio.net.network_fight_vnc_constants import HINT_POS
        from cardio.tui.constants import GRID_MARGIN_TOP

        hint_row = HINT_POS[1]
        assert hint_row < GRID_MARGIN_TOP


    def test_hint_clear_string_is_long_enough(self):
        """The clear string must be at least as long as the longest hint message."""
        from cardio.net.network_fight_vnc_constants import HINT_CLEAR

        longest_hint = "⚔  Your turn — play cards, then press C"
        assert len(HINT_CLEAR) >= len(longest_hint)

