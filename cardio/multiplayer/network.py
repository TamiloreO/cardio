"""Network module for LAN multiplayer communication.

Uses TCP sockets for reliable game state synchronization between players.
Messages are JSON-encoded with a simple framing protocol (length prefix).
"""

import json
import logging
import socket
import struct
import threading
from dataclasses import dataclass, asdict
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Tuple


class MessageType(Enum):
    # Lobby messages
    LOBBY_JOIN = auto()
    LOBBY_LEAVE = auto()
    LOBBY_UPDATE = auto()
    LOBBY_READY = auto()
    LOBBY_START = auto()

    # Game messages
    GAME_STATE = auto()
    PLAYER_ACTION = auto()
    CARD_PLAYED = auto()
    DECK_DRAW = auto()
    TURN_END = auto()
    FIGHT_END = auto()

    # Sync messages
    PING = auto()
    PONG = auto()
    ERROR = auto()


@dataclass
class NetworkMessage:
    """A message sent over the network."""

    type: MessageType
    data: Dict[str, Any]
    sender_id: str = ""

    def to_bytes(self) -> bytes:
        payload = json.dumps(
            {"type": self.type.name, "data": self.data, "sender_id": self.sender_id}
        ).encode("utf-8")
        return struct.pack(">I", len(payload)) + payload

    @classmethod
    def from_bytes(cls, data: bytes) -> "NetworkMessage":
        payload = json.loads(data.decode("utf-8"))
        return cls(
            type=MessageType[payload["type"]],
            data=payload["data"],
            sender_id=payload.get("sender_id", ""),
        )


class ConnectionHandler:
    """Handles a single client connection."""

    def __init__(
        self,
        conn: socket.socket,
        addr: Tuple[str, int],
        on_message: Callable[[socket.socket, NetworkMessage], None],
        on_disconnect: Callable[[socket.socket], None],
    ):
        self.conn = conn
        self.addr = addr
        self.on_message = on_message
        self.on_disconnect = on_disconnect
        self.running = False
        self.thread: Optional[threading.Thread] = None

    def start(self) -> None:
        self.running = True
        self.thread = threading.Thread(target=self._receive_loop, daemon=True)
        self.thread.start()

    def stop(self) -> None:
        self.running = False
        try:
            self.conn.close()
        except Exception:
            pass

    def _receive_loop(self) -> None:
        try:
            while self.running:
                # Read message length (4 bytes, big-endian)
                length_data = self._recv_exact(4)
                if not length_data:
                    break
                length = struct.unpack(">I", length_data)[0]

                # Read message payload
                payload = self._recv_exact(length)
                if not payload:
                    break

                message = NetworkMessage.from_bytes(payload)
                self.on_message(self.conn, message)

        except (ConnectionResetError, BrokenPipeError, OSError):
            pass
        finally:
            self.on_disconnect(self.conn)

    def _recv_exact(self, n: int) -> Optional[bytes]:
        """Receive exactly n bytes."""
        data = b""
        while len(data) < n:
            try:
                chunk = self.conn.recv(n - len(data))
                if not chunk:
                    return None
                data += chunk
            except (socket.timeout, OSError):
                return None
        return data

    def send(self, message: NetworkMessage) -> bool:
        try:
            self.conn.sendall(message.to_bytes())
            return True
        except (BrokenPipeError, OSError):
            return False


class MultiplayerServer:
    """Server for hosting multiplayer games."""

    DEFAULT_PORT = 5555

    def __init__(self, port: int = DEFAULT_PORT):
        self.port = port
        self.socket: Optional[socket.socket] = None
        self.clients: Dict[socket.socket, ConnectionHandler] = {}
        self.client_info: Dict[socket.socket, Dict[str, Any]] = {}
        self.running = False
        self.accept_thread: Optional[threading.Thread] = None
        self.message_handlers: Dict[
            MessageType, Callable[[socket.socket, NetworkMessage], None]
        ] = {}
        self.on_client_connected: Optional[Callable[[socket.socket], None]] = None
        self.on_client_disconnected: Optional[Callable[[socket.socket], None]] = None
        self._lock = threading.Lock()

    def register_handler(
        self,
        msg_type: MessageType,
        handler: Callable[[socket.socket, NetworkMessage], None],
    ) -> None:
        self.message_handlers[msg_type] = handler

    def start(self) -> bool:
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.bind(("0.0.0.0", self.port))
            self.socket.listen(5)
            self.socket.settimeout(1.0)
            self.running = True
            self.accept_thread = threading.Thread(target=self._accept_loop, daemon=True)
            self.accept_thread.start()
            logging.info("Server started on port %d", self.port)
            return True
        except OSError as e:
            logging.error("Failed to start server: %s", e)
            return False

    def stop(self) -> None:
        self.running = False
        with self._lock:
            for handler in list(self.clients.values()):
                handler.stop()
            self.clients.clear()
            self.client_info.clear()
        if self.socket:
            try:
                self.socket.close()
            except Exception:
                pass

    def _accept_loop(self) -> None:
        while self.running:
            try:
                conn, addr = self.socket.accept()
                conn.settimeout(30.0)
                handler = ConnectionHandler(
                    conn, addr, self._on_message, self._on_disconnect
                )
                with self._lock:
                    self.clients[conn] = handler
                    self.client_info[conn] = {"addr": addr}
                handler.start()
                logging.info("Client connected from %s", addr)
                if self.on_client_connected:
                    self.on_client_connected(conn)
            except socket.timeout:
                continue
            except OSError:
                break

    def _on_message(self, conn: socket.socket, message: NetworkMessage) -> None:
        if message.type in self.message_handlers:
            self.message_handlers[message.type](conn, message)

    def _on_disconnect(self, conn: socket.socket) -> None:
        with self._lock:
            if conn in self.clients:
                del self.clients[conn]
            if conn in self.client_info:
                del self.client_info[conn]
        logging.info("Client disconnected")
        if self.on_client_disconnected:
            self.on_client_disconnected(conn)

    def send_to(self, conn: socket.socket, message: NetworkMessage) -> bool:
        with self._lock:
            handler = self.clients.get(conn)
        if handler:
            return handler.send(message)
        return False

    def broadcast(
        self, message: NetworkMessage, exclude: Optional[socket.socket] = None
    ) -> None:
        with self._lock:
            clients = list(self.clients.items())
        for conn, handler in clients:
            if conn != exclude:
                handler.send(message)

    def get_client_count(self) -> int:
        with self._lock:
            return len(self.clients)

    def get_local_ip(self) -> str:
        """Get the local IP address for LAN connections."""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"


class MultiplayerClient:
    """Client for connecting to multiplayer games."""

    def __init__(self):
        self.socket: Optional[socket.socket] = None
        self.handler: Optional[ConnectionHandler] = None
        self.connected = False
        self.player_id: str = ""
        self.message_handlers: Dict[MessageType, Callable[[NetworkMessage], None]] = {}
        self.on_disconnected: Optional[Callable[[], None]] = None
        self._lock = threading.Lock()

    def register_handler(
        self, msg_type: MessageType, handler: Callable[[NetworkMessage], None]
    ) -> None:
        self.message_handlers[msg_type] = handler

    def connect(
        self, host: str, port: int = MultiplayerServer.DEFAULT_PORT, timeout: float = 5.0
    ) -> bool:
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(timeout)
            self.socket.connect((host, port))
            self.socket.settimeout(30.0)
            self.handler = ConnectionHandler(
                self.socket,
                (host, port),
                lambda _, msg: self._on_message(msg),
                lambda _: self._on_disconnect(),
            )
            self.handler.start()
            self.connected = True
            logging.info("Connected to server at %s:%d", host, port)
            return True
        except (socket.timeout, ConnectionRefusedError, OSError) as e:
            logging.error("Failed to connect: %s", e)
            return False

    def disconnect(self) -> None:
        self.connected = False
        if self.handler:
            self.handler.stop()
        if self.socket:
            try:
                self.socket.close()
            except Exception:
                pass

    def _on_message(self, message: NetworkMessage) -> None:
        if message.type in self.message_handlers:
            self.message_handlers[message.type](message)

    def _on_disconnect(self) -> None:
        self.connected = False
        logging.info("Disconnected from server")
        if self.on_disconnected:
            self.on_disconnected()

    def send(self, message: NetworkMessage) -> bool:
        if self.handler and self.connected:
            message.sender_id = self.player_id
            return self.handler.send(message)
        return False

    def is_connected(self) -> bool:
        return self.connected


def discover_servers(
    port: int = MultiplayerServer.DEFAULT_PORT, timeout: float = 2.0
) -> List[Tuple[str, int]]:
    """Discover servers on the local network using broadcast."""
    servers = []
    # Try common local network ranges
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
    except Exception:
        return servers

    # Extract network prefix
    prefix = ".".join(local_ip.split(".")[:-1])

    # Scan local network (simplified - just check a few IPs)
    for i in range(1, 255):
        host = f"{prefix}.{i}"
        try:
            test_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            test_socket.settimeout(0.1)
            result = test_socket.connect_ex((host, port))
            if result == 0:
                servers.append((host, port))
            test_socket.close()
        except Exception:
            pass

    return servers
