"""Lobby system for multiplayer matchmaking."""

import logging
import socket
import threading
import time
import uuid
from dataclasses import dataclass, field, asdict
from typing import Callable, Dict, List, Optional

from .network import (
    MessageType,
    MultiplayerClient,
    MultiplayerServer,
    NetworkMessage,
)


@dataclass
class LobbyPlayer:
    """Represents a player in the lobby."""

    id: str
    name: str
    ready: bool = False
    is_host: bool = False

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> "LobbyPlayer":
        return cls(**data)


class Lobby:
    """Manages the multiplayer lobby for matchmaking."""

    def __init__(self):
        self.players: Dict[str, LobbyPlayer] = {}
        self.server: Optional[MultiplayerServer] = None
        self.client: Optional[MultiplayerClient] = None
        self.is_host = False
        self.local_player: Optional[LobbyPlayer] = None
        self._conn_to_player: Dict[socket.socket, str] = {}
        self._player_to_conn: Dict[str, socket.socket] = {}
        self._lock = threading.Lock()

        # Callbacks for UI updates
        self.on_players_changed: Optional[Callable[[List[LobbyPlayer]], None]] = None
        self.on_game_start: Optional[Callable[[str], None]] = None
        self.on_error: Optional[Callable[[str], None]] = None
        self.on_disconnected: Optional[Callable[[], None]] = None

    def host_game(self, player_name: str, port: int = 5555) -> bool:
        """Start hosting a game lobby."""
        self.server = MultiplayerServer(port)
        self._setup_server_handlers()

        if not self.server.start():
            return False

        self.is_host = True
        self.local_player = LobbyPlayer(
            id=str(uuid.uuid4()), name=player_name, is_host=True, ready=True
        )

        with self._lock:
            self.players[self.local_player.id] = self.local_player

        self._notify_players_changed()
        logging.info("Hosting lobby as %s", player_name)
        return True

    def join_game(self, host: str, player_name: str, port: int = 5555) -> bool:
        """Join an existing game lobby."""
        self.client = MultiplayerClient()
        self._setup_client_handlers()

        if not self.client.connect(host, port):
            return False

        self.is_host = False
        self.local_player = LobbyPlayer(
            id=str(uuid.uuid4()), name=player_name, is_host=False
        )
        self.client.player_id = self.local_player.id

        # Send join message
        self.client.send(
            NetworkMessage(
                type=MessageType.LOBBY_JOIN,
                data=self.local_player.to_dict(),
                sender_id=self.local_player.id,
            )
        )

        logging.info("Joining lobby as %s", player_name)
        return True

    def leave_lobby(self) -> None:
        """Leave the current lobby."""
        if self.client and self.local_player:
            self.client.send(
                NetworkMessage(
                    type=MessageType.LOBBY_LEAVE,
                    data={"player_id": self.local_player.id},
                    sender_id=self.local_player.id,
                )
            )
            self.client.disconnect()

        if self.server:
            self.server.stop()

        with self._lock:
            self.players.clear()
            self._conn_to_player.clear()
            self._player_to_conn.clear()

        self.local_player = None
        self.is_host = False

    def set_ready(self, ready: bool) -> None:
        """Set the local player's ready status."""
        if not self.local_player:
            return

        self.local_player.ready = ready

        if self.is_host:
            with self._lock:
                if self.local_player.id in self.players:
                    self.players[self.local_player.id].ready = ready
            self._broadcast_lobby_update()
        elif self.client:
            self.client.send(
                NetworkMessage(
                    type=MessageType.LOBBY_READY,
                    data={"player_id": self.local_player.id, "ready": ready},
                    sender_id=self.local_player.id,
                )
            )

    def start_game(self) -> bool:
        """Start the game (host only). Returns True if game can start."""
        if not self.is_host:
            return False

        with self._lock:
            players = list(self.players.values())

        if len(players) < 2:
            if self.on_error:
                self.on_error("Need at least 2 players to start")
            return False

        if not all(p.ready for p in players):
            if self.on_error:
                self.on_error("Not all players are ready")
            return False

        # Generate shared seed for the game
        game_seed = str(int(time.time() * 1000))

        if self.server:
            self.server.broadcast(
                NetworkMessage(
                    type=MessageType.LOBBY_START,
                    data={"seed": game_seed, "players": [p.to_dict() for p in players]},
                )
            )

        if self.on_game_start:
            self.on_game_start(game_seed)

        return True

    def get_players(self) -> List[LobbyPlayer]:
        """Get list of all players in the lobby."""
        with self._lock:
            return list(self.players.values())

    def get_player_count(self) -> int:
        """Get number of players in the lobby."""
        with self._lock:
            return len(self.players)

    def get_host_ip(self) -> str:
        """Get the IP address for others to connect to."""
        if self.server:
            return self.server.get_local_ip()
        return ""

    def _setup_server_handlers(self) -> None:
        if not self.server:
            return

        self.server.register_handler(MessageType.LOBBY_JOIN, self._handle_server_join)
        self.server.register_handler(MessageType.LOBBY_LEAVE, self._handle_server_leave)
        self.server.register_handler(MessageType.LOBBY_READY, self._handle_server_ready)
        self.server.on_client_disconnected = self._handle_client_disconnected

    def _setup_client_handlers(self) -> None:
        if not self.client:
            return

        self.client.register_handler(
            MessageType.LOBBY_UPDATE, self._handle_client_update
        )
        self.client.register_handler(MessageType.LOBBY_START, self._handle_client_start)
        self.client.on_disconnected = self._handle_disconnected

    def _handle_server_join(
        self, conn: socket.socket, message: NetworkMessage
    ) -> None:
        """Handle player joining (server-side)."""
        player = LobbyPlayer.from_dict(message.data)

        with self._lock:
            self.players[player.id] = player
            self._conn_to_player[conn] = player.id
            self._player_to_conn[player.id] = conn

        logging.info("Player %s joined the lobby", player.name)
        self._broadcast_lobby_update()

    def _handle_server_leave(
        self, conn: socket.socket, message: NetworkMessage
    ) -> None:
        """Handle player leaving (server-side)."""
        player_id = message.data.get("player_id")
        self._remove_player(player_id)

    def _handle_server_ready(
        self, conn: socket.socket, message: NetworkMessage
    ) -> None:
        """Handle player ready status change (server-side)."""
        player_id = message.data.get("player_id")
        ready = message.data.get("ready", False)

        with self._lock:
            if player_id in self.players:
                self.players[player_id].ready = ready

        self._broadcast_lobby_update()

    def _handle_client_disconnected(self, conn: socket.socket) -> None:
        """Handle client disconnecting from server."""
        with self._lock:
            player_id = self._conn_to_player.get(conn)

        if player_id:
            self._remove_player(player_id)

    def _handle_client_update(self, message: NetworkMessage) -> None:
        """Handle lobby update from server (client-side)."""
        players_data = message.data.get("players", [])

        with self._lock:
            self.players.clear()
            for p_data in players_data:
                player = LobbyPlayer.from_dict(p_data)
                self.players[player.id] = player

        self._notify_players_changed()

    def _handle_client_start(self, message: NetworkMessage) -> None:
        """Handle game start from server (client-side)."""
        seed = message.data.get("seed")
        if self.on_game_start:
            self.on_game_start(seed)

    def _handle_disconnected(self) -> None:
        """Handle disconnection from server (client-side)."""
        with self._lock:
            self.players.clear()

        if self.on_disconnected:
            self.on_disconnected()

    def _remove_player(self, player_id: str) -> None:
        """Remove a player from the lobby."""
        with self._lock:
            if player_id in self.players:
                player = self.players[player_id]
                del self.players[player_id]
                logging.info("Player %s left the lobby", player.name)

            conn = self._player_to_conn.get(player_id)
            if conn:
                del self._player_to_conn[player_id]
                if conn in self._conn_to_player:
                    del self._conn_to_player[conn]

        self._broadcast_lobby_update()

    def _broadcast_lobby_update(self) -> None:
        """Broadcast current lobby state to all clients."""
        with self._lock:
            players = [p.to_dict() for p in self.players.values()]

        if self.server:
            self.server.broadcast(
                NetworkMessage(type=MessageType.LOBBY_UPDATE, data={"players": players})
            )

        self._notify_players_changed()

    def _notify_players_changed(self) -> None:
        """Notify UI of player list changes."""
        if self.on_players_changed:
            self.on_players_changed(self.get_players())
