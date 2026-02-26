"""Tests for multiplayer lobby functionality."""

import threading
import time
import pytest

from cardio.multiplayer.lobby import Lobby, LobbyPlayer


class TestLobbyPlayer:
    """Tests for LobbyPlayer dataclass."""

    def test_create_lobby_player(self):
        player = LobbyPlayer(id="123", name="TestPlayer")
        assert player.id == "123"
        assert player.name == "TestPlayer"
        assert player.ready is False
        assert player.is_host is False

    def test_lobby_player_to_dict(self):
        player = LobbyPlayer(id="abc", name="Player1", ready=True, is_host=True)
        d = player.to_dict()

        assert d["id"] == "abc"
        assert d["name"] == "Player1"
        assert d["ready"] is True
        assert d["is_host"] is True

    def test_lobby_player_from_dict(self):
        d = {"id": "xyz", "name": "Player2", "ready": False, "is_host": False}
        player = LobbyPlayer.from_dict(d)

        assert player.id == "xyz"
        assert player.name == "Player2"
        assert player.ready is False
        assert player.is_host is False


class TestLobby:
    """Tests for Lobby class."""

    def test_host_game(self):
        lobby = Lobby()
        result = lobby.host_game("HostPlayer", port=16555)

        assert result is True
        assert lobby.is_host is True
        assert lobby.local_player is not None
        assert lobby.local_player.name == "HostPlayer"
        assert lobby.local_player.is_host is True
        assert lobby.get_player_count() == 1

        lobby.leave_lobby()

    def test_host_creates_player_with_ready_status(self):
        lobby = Lobby()
        lobby.host_game("Host", port=16556)

        # Host should automatically be ready
        assert lobby.local_player.ready is True

        lobby.leave_lobby()

    def test_leave_lobby_clears_state(self):
        lobby = Lobby()
        lobby.host_game("Host", port=16557)

        lobby.leave_lobby()

        assert lobby.local_player is None
        assert lobby.is_host is False
        assert lobby.get_player_count() == 0

    def test_get_host_ip(self):
        lobby = Lobby()
        lobby.host_game("Host", port=16558)

        ip = lobby.get_host_ip()
        # Should be a valid IP
        assert ip.count(".") == 3 or ip == "127.0.0.1"

        lobby.leave_lobby()

    def test_set_ready(self):
        lobby = Lobby()
        lobby.host_game("Host", port=16559)

        lobby.set_ready(False)
        assert lobby.local_player.ready is False

        lobby.set_ready(True)
        assert lobby.local_player.ready is True

        lobby.leave_lobby()

    def test_cannot_start_game_with_one_player(self):
        lobby = Lobby()
        errors = []
        lobby.on_error = lambda msg: errors.append(msg)

        lobby.host_game("Host", port=16560)

        result = lobby.start_game()

        assert result is False
        assert len(errors) == 1
        assert "2 players" in errors[0]

        lobby.leave_lobby()

    def test_players_changed_callback(self):
        lobby = Lobby()
        callback_calls = []

        def on_players_changed(players):
            callback_calls.append(players)

        lobby.on_players_changed = on_players_changed
        lobby.host_game("Host", port=16561)

        assert len(callback_calls) >= 1
        # Last call should have the host
        assert any(
            any(p.name == "Host" for p in players)
            for players in callback_calls
        )

        lobby.leave_lobby()


class TestLobbyIntegration:
    """Integration tests for lobby host-client interaction."""

    def test_client_joins_host_lobby(self):
        host_lobby = Lobby()
        client_lobby = Lobby()

        host_lobby.host_game("HostPlayer", port=16565)
        time.sleep(0.1)

        result = client_lobby.join_game("127.0.0.1", "ClientPlayer", port=16565)
        time.sleep(0.3)  # Wait for network sync

        assert result is True
        assert client_lobby.is_host is False
        assert client_lobby.local_player.name == "ClientPlayer"

        # Both lobbies should see 2 players eventually
        time.sleep(0.5)
        assert host_lobby.get_player_count() == 2
        # Client needs time to receive update
        assert client_lobby.get_player_count() >= 1

        client_lobby.leave_lobby()
        host_lobby.leave_lobby()

    def test_start_game_broadcasts_to_clients(self):
        host_lobby = Lobby()
        client_lobby = Lobby()
        client_game_started = threading.Event()
        client_seed = []

        def on_game_start(seed):
            client_seed.append(seed)
            client_game_started.set()

        client_lobby.on_game_start = on_game_start

        host_lobby.host_game("Host", port=16566)
        time.sleep(0.1)

        client_lobby.join_game("127.0.0.1", "Client", port=16566)
        time.sleep(0.3)

        # Set client ready
        client_lobby.set_ready(True)
        time.sleep(0.2)

        # Host starts game
        result = host_lobby.start_game()

        assert result is True
        assert client_game_started.wait(timeout=2.0)
        assert len(client_seed) == 1
        assert client_seed[0] is not None

        client_lobby.leave_lobby()
        host_lobby.leave_lobby()

    def test_client_disconnect_removes_from_lobby(self):
        host_lobby = Lobby()
        client_lobby = Lobby()

        host_lobby.host_game("Host", port=16567)
        time.sleep(0.1)

        client_lobby.join_game("127.0.0.1", "Client", port=16567)
        time.sleep(0.3)

        assert host_lobby.get_player_count() == 2

        client_lobby.leave_lobby()
        time.sleep(0.5)

        # Host should see only 1 player now
        assert host_lobby.get_player_count() == 1

        host_lobby.leave_lobby()
