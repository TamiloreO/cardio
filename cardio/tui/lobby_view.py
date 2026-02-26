"""cardio.tui.lobby_view — LAN multiplayer lobby browser TUI.

This screen is shown after the player selects *vs Online Multiplayer* from the main
menu.  It gives the player two sub-choices:

**Host a lobby**
    The player opens a lobby under their name.  The screen shows a "Waiting for
    opponent…" spinner and live-refreshes to display how many other players are
    currently findable on the LAN (via the same UDP broadcast the host emits).  Once a
    guest connects the screen returns a ready TCP socket.

**Join a lobby**
    The player scans for open lobbies.  The screen live-updates the list every
    :data:`_REFRESH_INTERVAL` seconds while the player browses.  The player moves the
    cursor with ``↑``/``↓`` and presses ``Enter`` to join.  The screen connects to the
    chosen host and returns a ready TCP socket.

Both paths return a :class:`~cardio.net.lobby.ConnectionResult` named tuple:

``sock``
    The connected TCP socket that should be passed to
    :class:`~cardio.net.network_fight_vnc.NetworkFightVnC`.

``role``
    ``"host"`` or ``"guest"``.  The host's deck occupies the *opponent* (line 0/1)
    position from the guest's perspective and vice-versa.  Both sides run identical
    fight logic; only the animation labels differ slightly.

Navigation (join screen)
--------------------------
- ``↑`` / ``↓``  move through discovered lobbies.
- ``H``           switch to *host* mode.
- ``Enter``       join the highlighted lobby.
- ``Escape``      go back to the main menu (returns ``None``).

Navigation (host screen)
--------------------------
- ``Escape``      cancel hosting and go back to the main menu (returns ``None``).

Layout
------
The screen is split into three regions:

*Header*
    Mode title and key-binding hints.

*Lobby list / status area*
    In join mode: a scrolling list of discovered lobbies with live player counts.
    In host mode: a single status line plus a spinner.

*Footer*
    Persistent key hints.
"""

from __future__ import annotations

import time
import threading
from dataclasses import dataclass
from typing import List, Literal, Optional
import socket as _socket

from asciimatics.screen import Screen

from cardio.tui.tuibase import TUIBaseMixin
from cardio.tui.utils import dPos, show_text, get_keycode
from cardio.tui.constants import Color
from cardio.net.lobby import LobbyServer, LobbyClient, LobbyEntry, LOBBY_SCAN_DURATION

# ── layout ─────────────────────────────────────────────────────────────────────

_HEADER_Y = 2
_LIST_TOP_Y = 8          # First row of the lobby list.
_LIST_MAX_ROWS = 20      # Maximum visible lobby entries before truncation.
_FOOTER_Y_FROM_BOTTOM = 3

# How often (seconds) the join view polls for new lobbies while the player browses.
_REFRESH_INTERVAL = 1.0

# Spinner frames shown while the host is waiting.
_SPINNER = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]


# ── result type ────────────────────────────────────────────────────────────────


@dataclass
class ConnectionResult:
    """The outcome of a successful lobby interaction."""

    sock: _socket.socket
    role: Literal["host", "guest"]


# ── main view class ────────────────────────────────────────────────────────────


class TUILobbyView(TUIBaseMixin):
    """Lobby browser screen for LAN multiplayer.

    Parameters
    ----------
    player_name:
        The local player's name, used as the lobby title when hosting.
    debug:
        Forwarded to :class:`~cardio.tui.tuibase.TUIBaseMixin`.
    """

    def __init__(self, player_name: str, debug: bool = False) -> None:
        super().__init__(debug=debug)
        self._player_name = player_name

    # ── public entry point ─────────────────────────────────────────────────────

    def show(self) -> Optional[ConnectionResult]:
        """Show the lobby mode-selection screen and handle the full flow.

        Returns a :class:`ConnectionResult` when a connection is established, or
        ``None`` if the player pressed Escape to abort.
        """
        return self._mode_select()

    # ── mode selection ─────────────────────────────────────────────────────────

    def _mode_select(self) -> Optional[ConnectionResult]:
        """Let the player choose between hosting and joining."""
        cursor = 0
        options = ["  Host a lobby  ", "  Join a lobby  "]
        while True:
            self._draw_mode_select(cursor, options)
            keycode = get_keycode(self.screen)
            if keycode == Screen.KEY_UP:
                cursor = max(0, cursor - 1)
            elif keycode == Screen.KEY_DOWN:
                cursor = min(len(options) - 1, cursor + 1)
            elif keycode in (13,):  # Enter
                if cursor == 0:
                    return self._host_flow()
                else:
                    return self._join_flow()
            elif keycode == Screen.KEY_ESCAPE:
                return None

    def _draw_mode_select(self, cursor: int, options: List[str]) -> None:
        self.screen.clear_buffer(0, 0, 0)
        cx = self.screen.width // 2
        show_text(
            self.screen,
            dPos(cx - 11, _HEADER_Y),
            "⚔  Online Multiplayer  ⚔",
            color=Color.CYAN,
        )
        show_text(
            self.screen,
            dPos(cx - 20, _HEADER_Y + 2),
            "Choose your role for this session:",
            color=Color.GRAY,
        )
        for i, label in enumerate(options):
            y = _LIST_TOP_Y + i * 2
            if i == cursor:
                display = f"▶  {label.strip()}  ◀"
                col = Color.MAGENTA
            else:
                display = f"   {label.strip()}   "
                col = Color.WHITE
            show_text(self.screen, dPos(cx - len(display) // 2, y), display, color=col)
        footer = "↑↓ navigate   Enter confirm   Esc back to menu"
        show_text(
            self.screen,
            dPos(cx - len(footer) // 2, self.screen.height - _FOOTER_Y_FROM_BOTTOM),
            footer,
            color=Color.GRAY,
        )
        self.screen.refresh()

    # ── host flow ──────────────────────────────────────────────────────────────

    def _host_flow(self) -> Optional[ConnectionResult]:
        """Open a lobby and wait for a guest.  Returns when connected or aborted."""
        server = LobbyServer(player_name=self._player_name)
        server.start()

        # Run a background client so we can show how many OTHER players are visible.
        scanner = LobbyClient()
        scanner.start_scan()

        spinner_idx = 0
        result: Optional[ConnectionResult] = None
        connected = threading.Event()
        guest_sock: list = []  # mutable container for thread result

        def _wait_thread():
            try:
                s = server.wait_for_guest(timeout=300)
                guest_sock.append(s)
            except TimeoutError:
                pass
            connected.set()

        t = threading.Thread(target=_wait_thread, daemon=True)
        t.start()

        try:
            while not connected.is_set():
                entries = scanner.get_entries()
                # Exclude ourselves from the visible count.
                other_players = [
                    e for e in entries if e.host_name != self._player_name
                ]
                self._draw_host_waiting(
                    spinner=_SPINNER[spinner_idx % len(_SPINNER)],
                    other_lobbies=other_players,
                )
                spinner_idx += 1
                # Poll for Escape without blocking the spinner refresh.
                keycode = get_keycode(self.screen)
                if keycode == Screen.KEY_ESCAPE:
                    server.stop()
                    scanner.stop_scan()
                    return None
                connected.wait(timeout=0.15)
        finally:
            scanner.stop_scan()

        if guest_sock:
            result = ConnectionResult(sock=guest_sock[0], role="host")
        return result

    def _draw_host_waiting(
        self, spinner: str, other_lobbies: List[LobbyEntry]
    ) -> None:
        self.screen.clear_buffer(0, 0, 0)
        cx = self.screen.width // 2
        cy = self.screen.height // 2

        show_text(
            self.screen,
            dPos(cx - 12, _HEADER_Y),
            f"⚔  Hosting as: {self._player_name}  ⚔",
            color=Color.CYAN,
        )
        show_text(
            self.screen,
            dPos(cx - 18, _HEADER_Y + 2),
            "Your lobby is open.  Waiting for a challenger…",
            color=Color.WHITE,
        )
        show_text(
            self.screen,
            dPos(cx - 1, cy - 2),
            spinner,
            color=Color.YELLOW,
        )
        # ── other players on the LAN ───────────────────────────────────────────
        other_count = len(other_lobbies)
        count_label = (
            f"Other players currently findable on LAN: {other_count}"
            if other_count != 1
            else "1 other player currently findable on LAN"
        )
        show_text(
            self.screen,
            dPos(cx - len(count_label) // 2, cy),
            count_label,
            color=Color.GREEN if other_count > 0 else Color.GRAY,
        )
        if other_lobbies:
            show_text(
                self.screen,
                dPos(cx - 12, cy + 2),
                "Other open lobbies:",
                color=Color.GRAY,
            )
            for i, entry in enumerate(other_lobbies[: _LIST_MAX_ROWS]):
                show_text(
                    self.screen,
                    dPos(cx - 12, cy + 3 + i),
                    f"  {entry}",
                    color=Color.GRAY,
                )
        footer = "Esc  cancel hosting"
        show_text(
            self.screen,
            dPos(cx - len(footer) // 2, self.screen.height - _FOOTER_Y_FROM_BOTTOM),
            footer,
            color=Color.GRAY,
        )
        self.screen.refresh()

    # ── join flow ──────────────────────────────────────────────────────────────

    def _join_flow(self) -> Optional[ConnectionResult]:
        """Scan for lobbies and let the player pick one."""
        client = LobbyClient(scan_duration=LOBBY_SCAN_DURATION)
        client.start_scan()

        cursor = 0
        last_refresh = time.monotonic()

        try:
            while True:
                now = time.monotonic()
                if now - last_refresh >= _REFRESH_INTERVAL:
                    last_refresh = now

                entries = client.get_entries()
                if cursor >= len(entries) and entries:
                    cursor = len(entries) - 1

                self._draw_join_list(entries, cursor)
                keycode = get_keycode(self.screen)

                if keycode == Screen.KEY_UP:
                    cursor = max(0, cursor - 1)
                elif keycode == Screen.KEY_DOWN:
                    cursor = min(max(0, len(entries) - 1), cursor + 1)
                elif keycode in (13,):  # Enter
                    if entries:
                        chosen = entries[cursor]
                        client.stop_scan()
                        return self._do_connect(chosen)
                elif keycode == Screen.KEY_ESCAPE:
                    return None
        finally:
            client.stop_scan()

    def _draw_join_list(self, entries: List[LobbyEntry], cursor: int) -> None:
        self.screen.clear_buffer(0, 0, 0)
        cx = self.screen.width // 2

        show_text(
            self.screen,
            dPos(cx - 14, _HEADER_Y),
            "⚔  Join a Multiplayer Lobby  ⚔",
            color=Color.CYAN,
        )

        # ── live player count ──────────────────────────────────────────────────
        count = len(entries)
        if count == 0:
            count_str = "Scanning for open lobbies…  (0 found so far)"
        elif count == 1:
            count_str = "1 open lobby found:"
        else:
            count_str = f"{count} open lobbies found:"
        show_text(
            self.screen,
            dPos(cx - len(count_str) // 2, _HEADER_Y + 2),
            count_str,
            color=Color.GREEN if count > 0 else Color.GRAY,
        )

        # ── lobby list ─────────────────────────────────────────────────────────
        if not entries:
            hint = "No lobbies visible yet – ask a friend to start hosting!"
            show_text(
                self.screen,
                dPos(cx - len(hint) // 2, _LIST_TOP_Y + 2),
                hint,
                color=Color.GRAY,
            )
        else:
            for i, entry in enumerate(entries[:_LIST_MAX_ROWS]):
                y = _LIST_TOP_Y + i * 2
                label = str(entry)
                if i == cursor:
                    display = f"▶  {label}  ◀"
                    col = Color.MAGENTA
                else:
                    display = f"   {label}   "
                    col = Color.WHITE
                show_text(
                    self.screen,
                    dPos(cx - len(display) // 2, y),
                    display,
                    color=col,
                )
            if len(entries) > _LIST_MAX_ROWS:
                more = f"… and {len(entries) - _LIST_MAX_ROWS} more (scroll down)"
                show_text(
                    self.screen,
                    dPos(cx - len(more) // 2, _LIST_TOP_Y + _LIST_MAX_ROWS * 2),
                    more,
                    color=Color.GRAY,
                )

        footer = "↑↓ navigate   Enter join   Esc back"
        show_text(
            self.screen,
            dPos(cx - len(footer) // 2, self.screen.height - _FOOTER_Y_FROM_BOTTOM),
            footer,
            color=Color.GRAY,
        )
        self.screen.refresh()

    def _do_connect(self, entry: LobbyEntry) -> Optional[ConnectionResult]:
        """Attempt TCP connection to *entry* and return a :class:`ConnectionResult`."""
        self._draw_connecting(entry)
        try:
            client = LobbyClient()
            sock = client.connect_to(entry)
            return ConnectionResult(sock=sock, role="guest")
        except ConnectionError as exc:
            self.message(f"Could not connect: {exc}")
            return None

    def _draw_connecting(self, entry: LobbyEntry) -> None:
        self.screen.clear_buffer(0, 0, 0)
        cx = self.screen.width // 2
        cy = self.screen.height // 2
        msg = f"Connecting to {entry.host_name} …"
        show_text(
            self.screen,
            dPos(cx - len(msg) // 2, cy),
            msg,
            color=Color.YELLOW,
        )
        self.screen.refresh()
