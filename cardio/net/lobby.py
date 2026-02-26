"""cardio.net.lobby — LAN lobby discovery and coordination.

Architecture
------------
Discovery uses UDP broadcast so that no pre-shared IP address is needed.  Every host
who opens a lobby continuously broadcasts a small ``LOBBY_ANNOUNCE`` datagram on the
well-known port :data:`LOBBY_UDP_PORT`.  Any client who wants to find lobbies listens
on that same port and collects the datagrams it receives.

Once a guest decides to join a specific lobby the host is contacted over a TCP
connection on :data:`LOBBY_TCP_PORT`.  The host sends a one-line ``LOBBY_ACK``
datagram back, after which the connection is handed off to the fight layer.

Classes
-------
``LobbyEntry``
    Plain data object representing one discovered lobby.

``LobbyServer``
    Run by the player who *hosts* a lobby.  Starts two threads:
    - A UDP broadcaster that continuously announces the lobby.
    - A TCP acceptor that waits for exactly one guest to connect.
    Call :meth:`wait_for_guest` to block until a guest arrives; it returns the
    accepted TCP socket ready for fight traffic.

``LobbyClient``
    Run by the player who wants to *join* a lobby.  Listens on the broadcast port for
    a configurable window of time and collects :class:`LobbyEntry` objects.
    Call :meth:`connect_to` with the chosen entry to open a TCP connection to that
    host; it returns the socket ready for fight traffic.
"""

from __future__ import annotations

import json
import logging
import socket
import threading
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

log = logging.getLogger(__name__)

# ── network constants ──────────────────────────────────────────────────────────

LOBBY_UDP_PORT: int = 47823  # Broadcast / listen port for lobby announcements.
LOBBY_TCP_PORT: int = 47824  # TCP port the host listens on for incoming guests.
BROADCAST_ADDR: str = "255.255.255.255"
ANNOUNCE_INTERVAL: float = 1.0   # Seconds between UDP broadcasts.
LOBBY_SCAN_DURATION: float = 3.0  # Seconds the client listens for announcements.

# ── datagram payload keys ──────────────────────────────────────────────────────

_KEY_TYPE = "type"
_KEY_HOST_NAME = "host_name"
_KEY_HOST_IP = "host_ip"
_KEY_TCP_PORT = "tcp_port"

_TYPE_ANNOUNCE = "LOBBY_ANNOUNCE"
_TYPE_ACK = "LOBBY_ACK"


# ── data structures ────────────────────────────────────────────────────────────


@dataclass
class LobbyEntry:
    """One discovered lobby, as seen from the client side."""

    host_name: str          # Human-readable player name chosen by the host.
    host_ip: str            # IPv4 address of the host machine.
    tcp_port: int           # TCP port to connect to for fight traffic.
    last_seen: float = field(default_factory=time.monotonic, repr=False)

    def age(self) -> float:
        """Seconds since the last announcement was received from this host."""
        return time.monotonic() - self.last_seen

    def refresh(self) -> None:
        """Mark this entry as freshly seen."""
        self.last_seen = time.monotonic()

    def __str__(self) -> str:
        return f"{self.host_name}  ({self.host_ip})"


# ── server ─────────────────────────────────────────────────────────────────────


class LobbyServer:
    """Hosts a lobby: broadcasts presence over UDP, accepts one TCP guest.

    Parameters
    ----------
    player_name:
        The human-readable name shown to scanning clients.
    tcp_port:
        TCP port to listen on.  Override only in tests.
    udp_port:
        UDP broadcast port.  Override only in tests.
    """

    def __init__(
        self,
        player_name: str,
        tcp_port: int = LOBBY_TCP_PORT,
        udp_port: int = LOBBY_UDP_PORT,
    ) -> None:
        self.player_name = player_name
        self.tcp_port = tcp_port
        self.udp_port = udp_port

        self._stop_event = threading.Event()
        self._guest_socket: Optional[socket.socket] = None
        self._guest_arrived = threading.Event()

        self._broadcaster_thread = threading.Thread(
            target=self._broadcast_loop, daemon=True, name="LobbyBroadcaster"
        )
        self._acceptor_thread = threading.Thread(
            target=self._accept_loop, daemon=True, name="LobbyAcceptor"
        )

    # ── public interface ───────────────────────────────────────────────────────

    def start(self) -> None:
        """Start background threads.  Call before :meth:`wait_for_guest`."""
        self._acceptor_thread.start()
        # Give the acceptor a moment to bind before we start advertising.
        time.sleep(0.05)
        self._broadcaster_thread.start()
        log.info("LobbyServer started (player=%r, tcp=%d)", self.player_name, self.tcp_port)

    def wait_for_guest(self, timeout: Optional[float] = None) -> socket.socket:
        """Block until a guest connects.  Returns the TCP socket for fight traffic.

        Raises ``TimeoutError`` if *timeout* seconds elapse with no guest.
        """
        arrived = self._guest_arrived.wait(timeout=timeout)
        self.stop()
        if not arrived or self._guest_socket is None:
            raise TimeoutError("No guest connected within the timeout window.")
        return self._guest_socket

    def stop(self) -> None:
        """Signal background threads to exit.  Safe to call multiple times."""
        self._stop_event.set()

    # ── background threads ─────────────────────────────────────────────────────

    def _broadcast_loop(self) -> None:
        """Continuously broadcast a UDP ``LOBBY_ANNOUNCE`` datagram."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            payload = json.dumps(
                {
                    _KEY_TYPE: _TYPE_ANNOUNCE,
                    _KEY_HOST_NAME: self.player_name,
                    _KEY_TCP_PORT: self.tcp_port,
                }
            ).encode("utf-8")
            while not self._stop_event.is_set():
                try:
                    sock.sendto(payload, (BROADCAST_ADDR, self.udp_port))
                except OSError as exc:
                    log.warning("Broadcast failed: %s", exc)
                self._stop_event.wait(timeout=ANNOUNCE_INTERVAL)
        finally:
            sock.close()
            log.debug("LobbyServer broadcaster stopped.")

    def _accept_loop(self) -> None:
        """Accept the first incoming TCP connection from a guest."""
        try:
            server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server_sock.bind(("", self.tcp_port))
            server_sock.listen(1)
            server_sock.settimeout(1.0)  # Poll so we can check _stop_event.
            log.debug("LobbyServer TCP acceptor listening on port %d", self.tcp_port)
            while not self._stop_event.is_set():
                try:
                    conn, addr = server_sock.accept()
                    log.info("Guest connected from %s", addr)
                    # Send ACK so the guest knows the connection is accepted.
                    ack = json.dumps({_KEY_TYPE: _TYPE_ACK}).encode("utf-8")
                    conn.sendall(ack + b"\n")
                    self._guest_socket = conn
                    self._guest_arrived.set()
                    return
                except socket.timeout:
                    pass
        except Exception as exc:
            log.error("LobbyServer acceptor error: %s", exc)
        finally:
            server_sock.close()
            log.debug("LobbyServer TCP acceptor stopped.")


# ── client ─────────────────────────────────────────────────────────────────────


class LobbyClient:
    """Discovers lobbies on the LAN and connects to a chosen host.

    Parameters
    ----------
    udp_port:
        UDP broadcast port to listen on.  Override only in tests.
    scan_duration:
        How many seconds to listen for announcements before returning results.
    """

    def __init__(
        self,
        udp_port: int = LOBBY_UDP_PORT,
        scan_duration: float = LOBBY_SCAN_DURATION,
    ) -> None:
        self.udp_port = udp_port
        self.scan_duration = scan_duration
        # host_ip → LobbyEntry, deduplicated by IP so we don't list the same host twice.
        self._entries: Dict[str, LobbyEntry] = {}
        self._lock = threading.Lock()
        self._stop_event = threading.Event()

    # ── public interface ───────────────────────────────────────────────────────

    def start_scan(self) -> None:
        """Begin listening for UDP announcements in a background thread."""
        self._listener_thread = threading.Thread(
            target=self._listen_loop, daemon=True, name="LobbyScanner"
        )
        self._listener_thread.start()

    def stop_scan(self) -> None:
        """Stop the background listener."""
        self._stop_event.set()

    def get_entries(self) -> List[LobbyEntry]:
        """Return a snapshot of currently known lobbies, sorted by host name."""
        with self._lock:
            return sorted(self._entries.values(), key=lambda e: e.host_name.lower())

    def connect_to(self, entry: LobbyEntry) -> socket.socket:
        """Open a TCP connection to the lobby described by *entry*.

        Blocks briefly while waiting for the host's ACK.
        Returns the TCP socket ready for fight traffic.
        Raises ``ConnectionError`` on failure.
        """
        self.stop_scan()
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5.0)
            sock.connect((entry.host_ip, entry.tcp_port))
            # Read until newline to consume the host's ACK line.
            buf = b""
            while b"\n" not in buf:
                chunk = sock.recv(256)
                if not chunk:
                    raise ConnectionError("Host closed connection before sending ACK.")
                buf += chunk
            ack = json.loads(buf.split(b"\n")[0].decode("utf-8"))
            if ack.get(_KEY_TYPE) != _TYPE_ACK:
                raise ConnectionError(f"Unexpected ACK payload: {ack!r}")
            sock.settimeout(None)  # Return a blocking socket for fight traffic.
            log.info("Connected to lobby %r at %s:%d", entry.host_name, entry.host_ip, entry.tcp_port)
            return sock
        except OSError as exc:
            raise ConnectionError(f"Could not connect to {entry.host_ip}: {exc}") from exc

    # ── background thread ──────────────────────────────────────────────────────

    def _listen_loop(self) -> None:
        """Listen for UDP ``LOBBY_ANNOUNCE`` datagrams and populate ``_entries``."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.bind(("", self.udp_port))
            sock.settimeout(0.5)
            log.debug("LobbyClient scanner listening on UDP port %d", self.udp_port)
            while not self._stop_event.is_set():
                try:
                    data, addr = sock.recvfrom(4096)
                    self._handle_datagram(data, addr[0])
                except socket.timeout:
                    pass
        except Exception as exc:
            log.error("LobbyClient listener error: %s", exc)
        finally:
            sock.close()
            log.debug("LobbyClient scanner stopped.")

    def _handle_datagram(self, data: bytes, sender_ip: str) -> None:
        """Parse one UDP datagram and update ``_entries``."""
        try:
            msg = json.loads(data.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return
        if msg.get(_KEY_TYPE) != _TYPE_ANNOUNCE:
            return
        host_name = str(msg.get(_KEY_HOST_NAME, "Unknown"))
        tcp_port = int(msg.get(_KEY_TCP_PORT, LOBBY_TCP_PORT))
        with self._lock:
            if sender_ip in self._entries:
                self._entries[sender_ip].refresh()
            else:
                self._entries[sender_ip] = LobbyEntry(
                    host_name=host_name,
                    host_ip=sender_ip,
                    tcp_port=tcp_port,
                )
                log.info("Discovered lobby: %r at %s:%d", host_name, sender_ip, tcp_port)
