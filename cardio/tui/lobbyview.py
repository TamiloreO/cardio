"""Lobby TUI for multiplayer matchmaking."""

import threading
import time
from typing import List, Optional

from asciimatics.screen import Screen

from cardio.multiplayer.lobby import Lobby, LobbyPlayer
from .tuibase import TUIBaseMixin
from .utils import show_text, get_keycode, dPos
from .constants import Color


class TUILobbyView(TUIBaseMixin):
    """TUI view for the multiplayer lobby."""

    def __init__(self, lobby: Lobby, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.lobby = lobby
        self.players: List[LobbyPlayer] = []
        self.game_started = False
        self.game_seed: Optional[str] = None
        self.error_message: Optional[str] = None
        self.disconnected = False
        self._refresh_needed = True
        self._lock = threading.Lock()

        # Set up lobby callbacks
        self.lobby.on_players_changed = self._on_players_changed
        self.lobby.on_game_start = self._on_game_start
        self.lobby.on_error = self._on_error
        self.lobby.on_disconnected = self._on_disconnected

    def _on_players_changed(self, players: List[LobbyPlayer]) -> None:
        """Callback when player list changes."""
        with self._lock:
            self.players = players
            self._refresh_needed = True

    def _on_game_start(self, seed: str) -> None:
        """Callback when game starts."""
        with self._lock:
            self.game_started = True
            self.game_seed = seed

    def _on_error(self, message: str) -> None:
        """Callback when an error occurs."""
        with self._lock:
            self.error_message = message
            self._refresh_needed = True

    def _on_disconnected(self) -> None:
        """Callback when disconnected from server."""
        with self._lock:
            self.disconnected = True
            self._refresh_needed = True

    def show(self) -> Optional[str]:
        """Display the lobby view.

        Returns the game seed if game starts, None if cancelled.
        """
        while True:
            with self._lock:
                if self.game_started:
                    return self.game_seed
                if self.disconnected:
                    self.message("Disconnected from server")
                    return None
                refresh = self._refresh_needed
                self._refresh_needed = False

            if refresh:
                self._draw_lobby()

            keycode = get_keycode(self.screen)

            if keycode == ord("r") or keycode == ord("R"):
                self._toggle_ready()
            elif keycode == ord("s") or keycode == ord("S"):
                if self.lobby.is_host:
                    self.lobby.start_game()
            elif keycode == 27 or keycode == ord("q") or keycode == ord("Q"):
                self.lobby.leave_lobby()
                return None

            # Small delay to prevent busy-waiting
            time.sleep(0.05)

    def _toggle_ready(self) -> None:
        """Toggle the local player's ready status."""
        if self.lobby.local_player:
            new_ready = not self.lobby.local_player.ready
            self.lobby.set_ready(new_ready)

    def _draw_lobby(self) -> None:
        """Draw the lobby interface."""
        self.screen.clear_buffer(0, 0, 0)

        # Title
        title = "MULTIPLAYER LOBBY"
        if self.lobby.is_host:
            title += " (HOST)"
        x = (self.screen.width - len(title)) // 2
        show_text(self.screen, dPos(x, 3), title, color=Color.CYAN)

        # Connection info (for host)
        if self.lobby.is_host:
            ip = self.lobby.get_host_ip()
            info = f"Others can join at: {ip}"
            x = (self.screen.width - len(info)) // 2
            show_text(self.screen, dPos(x, 5), info, color=Color.YELLOW)

        # Player list header
        y = 10
        header = "Players in Lobby:"
        x = (self.screen.width - 50) // 2
        show_text(self.screen, dPos(x, y), header, color=Color.WHITE)
        y += 2

        # Player list
        with self._lock:
            players = list(self.players)

        if not players:
            show_text(self.screen, dPos(x, y), "No players yet...", color=Color.GRAY)
        else:
            for i, player in enumerate(players):
                # Player name
                name = player.name
                if player.is_host:
                    name += " (Host)"
                if self.lobby.local_player and player.id == self.lobby.local_player.id:
                    name += " (You)"

                # Ready status
                status = "✓ Ready" if player.ready else "○ Not Ready"
                status_color = Color.GREEN if player.ready else Color.RED

                line = f"  {i + 1}. {name:30s}"
                show_text(self.screen, dPos(x, y + i), line, color=Color.WHITE)
                show_text(
                    self.screen, dPos(x + len(line) + 2, y + i), status, color=status_color
                )

        # Player count
        count_text = f"Players: {len(players)}/2"
        x = (self.screen.width - len(count_text)) // 2
        show_text(self.screen, dPos(x, y + 8), count_text, color=Color.WHITE)

        # Error message
        with self._lock:
            error = self.error_message
            self.error_message = None

        if error:
            x = (self.screen.width - len(error)) // 2
            show_text(self.screen, dPos(x, y + 10), error, color=Color.RED)

        # Instructions
        instructions_y = self.screen.height - 6
        instructions = [
            "[R] Toggle Ready",
        ]
        if self.lobby.is_host:
            instructions.append("[S] Start Game (when all ready)")
        instructions.append("[Q] Leave Lobby")

        for i, inst in enumerate(instructions):
            x = (self.screen.width - len(inst)) // 2
            show_text(
                self.screen, dPos(x, instructions_y + i), inst, color=Color.GRAY
            )

        self.screen.refresh()


class TUIServerBrowser(TUIBaseMixin):
    """TUI for browsing available servers."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.servers: List[tuple] = []
        self.scanning = False

    def show(self) -> Optional[str]:
        """Display server browser. Returns selected server IP or None."""
        cursor = 0
        manual_ip = ""

        while True:
            self._draw_browser(cursor, manual_ip)
            keycode = get_keycode(self.screen)

            if keycode is None:
                continue
            elif keycode == Screen.KEY_UP:
                cursor = max(0, cursor - 1)
            elif keycode == Screen.KEY_DOWN:
                cursor = min(len(self.servers), cursor + 1)  # +1 for manual entry
            elif keycode in (13, Screen.KEY_ENTER):
                if cursor < len(self.servers):
                    return self.servers[cursor][0]
                elif manual_ip:
                    return manual_ip
            elif keycode == 27:  # Escape
                return None
            elif cursor == len(self.servers):  # Manual IP entry mode
                if keycode == Screen.KEY_BACK or keycode == 127:
                    manual_ip = manual_ip[:-1]
                elif 32 <= keycode <= 126:
                    manual_ip += chr(keycode)

    def _draw_browser(self, cursor: int, manual_ip: str) -> None:
        """Draw the server browser interface."""
        self.screen.clear_buffer(0, 0, 0)

        # Title
        title = "JOIN GAME"
        x = (self.screen.width - len(title)) // 2
        show_text(self.screen, dPos(x, 3), title, color=Color.CYAN)

        # Instructions
        subtitle = "Enter the host's IP address to connect:"
        x = (self.screen.width - len(subtitle)) // 2
        show_text(self.screen, dPos(x, 6), subtitle, color=Color.WHITE)

        # Manual IP entry
        y = 10
        x = (self.screen.width - 50) // 2

        is_selected = cursor == len(self.servers)
        if is_selected:
            prefix = "> "
            color = Color.YELLOW
        else:
            prefix = "  "
            color = Color.WHITE

        show_text(
            self.screen,
            dPos(x, y),
            f"{prefix}Enter IP: {manual_ip}_" if is_selected else f"{prefix}Enter IP: {manual_ip}",
            color=color,
        )

        # Server list (if any discovered)
        if self.servers:
            y += 3
            show_text(self.screen, dPos(x, y), "Discovered servers:", color=Color.WHITE)
            y += 1
            for i, (ip, port) in enumerate(self.servers):
                is_selected = cursor == i
                prefix = "> " if is_selected else "  "
                color = Color.YELLOW if is_selected else Color.WHITE
                show_text(
                    self.screen,
                    dPos(x, y + i),
                    f"{prefix}{ip}:{port}",
                    color=color,
                )

        # Instructions at bottom
        instructions = "Enter to connect, Esc to go back"
        x = (self.screen.width - len(instructions)) // 2
        show_text(
            self.screen,
            dPos(x, self.screen.height - 3),
            instructions,
            color=Color.GRAY,
        )

        self.screen.refresh()
