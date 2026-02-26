"""Tests for cardio.net.lobby — LAN discovery and TCP handshake.

All tests use real loopback sockets to avoid mocking the network stack, which would
make the tests brittle and obscure real bugs.  Tests that involve timing are given
generous timeouts so they pass on slow CI machines; they should complete in well under
a second on any modern machine.
"""

import json
import socket
import threading
import time
import pytest

from cardio.net.lobby import (
    LobbyServer,
    LobbyClient,
    LobbyEntry,
    LOBBY_TCP_PORT,
    LOBBY_UDP_PORT,
    _TYPE_ANNOUNCE,
    _TYPE_ACK,
    _KEY_TYPE,
    _KEY_HOST_NAME,
    _KEY_TCP_PORT,
)


# ── helpers ────────────────────────────────────────────────────────────────────


def _free_port() -> int:
    """Bind to port 0 and return the OS-assigned free port number."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _free_udp_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


# ── LobbyEntry ─────────────────────────────────────────────────────────────────


class TestLobbyEntry:
    def test_str_contains_name_and_ip(self):
        entry = LobbyEntry(host_name="Alice", host_ip="192.168.1.10", tcp_port=47824)
        s = str(entry)
        assert "Alice" in s
        assert "192.168.1.10" in s

    def test_age_grows_over_time(self):
        entry = LobbyEntry(host_name="Bob", host_ip="10.0.0.1", tcp_port=47824)
        time.sleep(0.05)
        assert entry.age() >= 0.04

    def test_refresh_resets_age(self):
        entry = LobbyEntry(host_name="Carol", host_ip="10.0.0.2", tcp_port=47824)
        time.sleep(0.1)
        entry.refresh()
        assert entry.age() < 0.05


# ── LobbyServer ────────────────────────────────────────────────────────────────


class TestLobbyServer:
    def test_server_accepts_tcp_connection_and_sends_ack(self):
        """A guest TCP connection should receive a newline-terminated ACK JSON."""
        tcp_port = _free_port()
        udp_port = _free_udp_port()
        server = LobbyServer("TestHost", tcp_port=tcp_port, udp_port=udp_port)
        server.start()

        # Give the acceptor a moment to bind.
        time.sleep(0.1)

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3.0)
        sock.connect(("127.0.0.1", tcp_port))

        buf = b""
        while b"\n" not in buf:
            buf += sock.recv(256)
        ack = json.loads(buf.split(b"\n")[0])
        assert ack[_KEY_TYPE] == _TYPE_ACK

        guest = server.wait_for_guest(timeout=3.0)
        assert guest is not None
        sock.close()
        guest.close()

    def test_wait_for_guest_returns_socket(self):
        """wait_for_guest returns a socket.socket on success."""
        tcp_port = _free_port()
        udp_port = _free_udp_port()
        server = LobbyServer("TestHost2", tcp_port=tcp_port, udp_port=udp_port)
        server.start()
        time.sleep(0.1)

        result = []

        def _connect():
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(3.0)
            s.connect(("127.0.0.1", tcp_port))
            buf = b""
            while b"\n" not in buf:
                buf += s.recv(256)
            result.append(s)

        t = threading.Thread(target=_connect, daemon=True)
        t.start()

        guest = server.wait_for_guest(timeout=5.0)
        assert isinstance(guest, socket.socket)
        t.join(timeout=3)
        for s in result:
            s.close()
        guest.close()

    def test_wait_for_guest_raises_timeout_error(self):
        """wait_for_guest should raise TimeoutError when no guest arrives."""
        tcp_port = _free_port()
        udp_port = _free_udp_port()
        server = LobbyServer("HostNoGuest", tcp_port=tcp_port, udp_port=udp_port)
        server.start()
        with pytest.raises(TimeoutError):
            server.wait_for_guest(timeout=0.3)

    def test_stop_is_idempotent(self):
        """Calling stop() more than once must not raise."""
        tcp_port = _free_port()
        udp_port = _free_udp_port()
        server = LobbyServer("HostStop", tcp_port=tcp_port, udp_port=udp_port)
        server.start()
        server.stop()
        server.stop()  # Second call must be harmless.


# ── LobbyClient ────────────────────────────────────────────────────────────────


class TestLobbyClient:
    def test_client_discovers_server_via_udp(self):
        """Client must see the server within a short scan window."""
        udp_port = _free_udp_port()
        tcp_port = _free_port()
        server = LobbyServer("Discoverable", tcp_port=tcp_port, udp_port=udp_port)
        server.start()

        client = LobbyClient(udp_port=udp_port, scan_duration=2.0)
        client.start_scan()
        # Wait up to 2 s for the broadcast to arrive.
        deadline = time.monotonic() + 2.0
        while time.monotonic() < deadline:
            if client.get_entries():
                break
            time.sleep(0.1)

        entries = client.get_entries()
        client.stop_scan()
        server.stop()

        assert len(entries) >= 1
        names = [e.host_name for e in entries]
        assert "Discoverable" in names

    def test_client_deduplicates_same_host(self):
        """Multiple datagrams from the same IP must not create duplicate entries."""
        udp_port = _free_udp_port()
        tcp_port = _free_port()
        server = LobbyServer("DedupHost", tcp_port=tcp_port, udp_port=udp_port)
        server.start()

        client = LobbyClient(udp_port=udp_port, scan_duration=2.0)
        client.start_scan()
        time.sleep(1.5)  # Let a few broadcast cycles pass.
        entries = client.get_entries()
        client.stop_scan()
        server.stop()

        # Even after multiple broadcasts, there should be at most one entry per host.
        ips = [e.host_ip for e in entries]
        assert len(ips) == len(set(ips)), "Duplicate entries found for the same IP"

    def test_client_connect_to_returns_socket(self):
        """connect_to should return a working socket after a full handshake."""
        tcp_port = _free_port()
        udp_port = _free_udp_port()
        server = LobbyServer("ConnectHost", tcp_port=tcp_port, udp_port=udp_port)
        server.start()
        time.sleep(0.1)

        entry = LobbyEntry(
            host_name="ConnectHost", host_ip="127.0.0.1", tcp_port=tcp_port
        )
        client = LobbyClient(udp_port=udp_port)

        guest_sock = None
        host_sock = None

        def _wait():
            nonlocal host_sock
            host_sock = server.wait_for_guest(timeout=5.0)

        t = threading.Thread(target=_wait, daemon=True)
        t.start()

        guest_sock = client.connect_to(entry)
        t.join(timeout=5)

        assert isinstance(guest_sock, socket.socket)
        assert isinstance(host_sock, socket.socket)
        guest_sock.close()
        host_sock.close()

    def test_connect_to_raises_on_no_server(self):
        """connect_to must raise ConnectionError when nothing is listening."""
        entry = LobbyEntry(
            host_name="Ghost", host_ip="127.0.0.1", tcp_port=_free_port()
        )
        client = LobbyClient()
        with pytest.raises(ConnectionError):
            client.connect_to(entry)

    def test_get_entries_sorted_by_name(self):
        """get_entries returns lobbies sorted alphabetically by host_name."""
        client = LobbyClient()
        # Inject entries directly to avoid needing a live network.
        client._entries = {
            "10.0.0.3": LobbyEntry("Zara", "10.0.0.3", 47824),
            "10.0.0.1": LobbyEntry("Alice", "10.0.0.1", 47824),
            "10.0.0.2": LobbyEntry("bob", "10.0.0.2", 47824),
        }
        entries = client.get_entries()
        names = [e.host_name for e in entries]
        assert names == sorted(names, key=str.lower)

    def test_stop_scan_is_idempotent(self):
        """stop_scan called twice must not raise."""
        client = LobbyClient()
        client.start_scan()
        time.sleep(0.05)
        client.stop_scan()
        client.stop_scan()


# ── full handshake integration ─────────────────────────────────────────────────


class TestFullHandshake:
    def test_host_and_guest_can_exchange_data_after_handshake(self):
        """After the lobby handshake, both sides can send arbitrary bytes."""
        tcp_port = _free_port()
        udp_port = _free_udp_port()
        server = LobbyServer("IntegrationHost", tcp_port=tcp_port, udp_port=udp_port)
        server.start()
        time.sleep(0.1)

        entry = LobbyEntry("IntegrationHost", "127.0.0.1", tcp_port)
        client = LobbyClient(udp_port=udp_port)

        host_sock = None

        def _wait():
            nonlocal host_sock
            host_sock = server.wait_for_guest(timeout=5.0)

        t = threading.Thread(target=_wait, daemon=True)
        t.start()

        guest_sock = client.connect_to(entry)
        t.join(timeout=5)

        # Send a test message from guest → host.
        guest_sock.sendall(b"PING\n")
        data = b""
        host_sock.settimeout(2.0)
        while b"\n" not in data:
            data += host_sock.recv(64)
        assert data.strip() == b"PING"

        guest_sock.close()
        host_sock.close()
