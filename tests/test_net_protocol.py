"""Tests for cardio.net.protocol — wire protocol framing and card serialisation."""

import json
import socket
import struct
import threading
import pytest

from cardio.net.protocol import (
    _HEADER_FMT,
    _HEADER_SIZE,
    _send_raw,
    _recv_raw,
    send_message,
    recv_message,
    make_fight_cards_msg,
    make_fight_done_msg,
    serialise_card_placement,
    deserialise_card,
    MSG_FIGHT_CARDS,
    MSG_FIGHT_DONE,
)
from cardio.card import Card
from cardio import skills


# ── helpers ────────────────────────────────────────────────────────────────────


def make_loopback_pair():
    """Return a connected (client, server) socket pair using a real loopback socket."""
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


def _send_in_thread(sock, data):
    """Send raw bytes in a background thread so the test can recv concurrently."""
    t = threading.Thread(target=lambda: sock.sendall(data), daemon=True)
    t.start()
    return t


# ── framing ────────────────────────────────────────────────────────────────────


class TestFraming:
    def test_header_size_is_4(self):
        assert _HEADER_SIZE == 4

    def test_send_recv_raw_round_trip(self):
        cli, srv = make_loopback_pair()
        payload = b"hello world"
        t = threading.Thread(target=_send_raw, args=(cli, payload), daemon=True)
        t.start()
        received = _recv_raw(srv)
        t.join(timeout=2)
        assert received == payload
        cli.close()
        srv.close()

    def test_send_recv_large_payload(self):
        cli, srv = make_loopback_pair()
        payload = b"x" * 65536
        t = threading.Thread(target=_send_raw, args=(cli, payload), daemon=True)
        t.start()
        received = _recv_raw(srv)
        t.join(timeout=5)
        assert received == payload
        cli.close()
        srv.close()

    def test_recv_raw_raises_on_closed_connection(self):
        cli, srv = make_loopback_pair()
        cli.close()
        with pytest.raises(ConnectionError):
            _recv_raw(srv)
        srv.close()

    def test_header_encodes_payload_length(self):
        cli, srv = make_loopback_pair()
        payload = b"abc"

        def _send():
            _send_raw(cli, payload)

        t = threading.Thread(target=_send, daemon=True)
        t.start()
        # Read the raw 4-byte header first.
        header = b""
        while len(header) < 4:
            header += srv.recv(4 - len(header))
        (length,) = struct.unpack(_HEADER_FMT, header)
        assert length == len(payload)
        t.join(timeout=2)
        cli.close()
        srv.close()


# ── high-level message helpers ─────────────────────────────────────────────────


class TestMessageHelpers:
    def test_send_recv_message_round_trip(self):
        cli, srv = make_loopback_pair()
        msg = {"type": "TEST", "value": 42, "nested": {"x": [1, 2, 3]}}
        t = threading.Thread(target=send_message, args=(cli, msg), daemon=True)
        t.start()
        received = recv_message(srv)
        t.join(timeout=2)
        assert received == msg
        cli.close()
        srv.close()

    def test_multiple_messages_do_not_interleave(self):
        """Send three messages; each should arrive complete and in order."""
        cli, srv = make_loopback_pair()
        messages = [{"seq": i, "data": "A" * (i * 100)} for i in range(3)]

        def _send_all():
            for m in messages:
                send_message(cli, m)

        t = threading.Thread(target=_send_all, daemon=True)
        t.start()
        received = [recv_message(srv) for _ in messages]
        t.join(timeout=5)
        assert received == messages
        cli.close()
        srv.close()

    def test_unicode_payload_survives_round_trip(self):
        cli, srv = make_loopback_pair()
        msg = {"emoji": "🐹🔥💎", "japanese": "カードゲーム"}
        t = threading.Thread(target=send_message, args=(cli, msg), daemon=True)
        t.start()
        received = recv_message(srv)
        t.join(timeout=2)
        assert received == msg
        cli.close()
        srv.close()


# ── typed constructors ─────────────────────────────────────────────────────────


class TestTypedConstructors:
    def test_make_fight_cards_msg_type_field(self):
        msg = make_fight_cards_msg([])
        assert msg["type"] == MSG_FIGHT_CARDS

    def test_make_fight_cards_msg_carries_cards(self):
        cards = [{"slot": 0, "name": "Cat", "power": 1, "health": 2,
                  "costs_fire": 0, "costs_spirits": 1, "has_fire": 1,
                  "has_spirits": 1, "skills": []}]
        msg = make_fight_cards_msg(cards)
        assert msg["cards"] == cards

    def test_make_fight_done_msg_type_field(self):
        msg = make_fight_done_msg()
        assert msg["type"] == MSG_FIGHT_DONE

    def test_make_fight_done_msg_has_no_extra_keys(self):
        msg = make_fight_done_msg()
        assert set(msg.keys()) == {"type"}


# ── card serialisation ─────────────────────────────────────────────────────────


class TestCardSerialisation:
    def _plain_card(self):
        return Card(
            name="Fox",
            power=2,
            health=3,
            costs_fire=1,
            costs_spirits=0,
            has_fire=1,
            has_spirits=1,
        )

    def _skilled_card(self):
        return Card(
            name="Porcupine",
            power=1,
            health=4,
            costs_fire=0,
            costs_spirits=1,
            has_fire=1,
            has_spirits=1,
            skills=[skills.Spines, skills.Shield],
        )

    def test_serialise_produces_correct_slot(self):
        d = serialise_card_placement(2, self._plain_card())
        assert d["slot"] == 2

    def test_serialise_preserves_all_numeric_attributes(self):
        card = self._plain_card()
        d = serialise_card_placement(0, card)
        assert d["name"] == card.name
        assert d["power"] == card.power
        assert d["health"] == card.health
        assert d["costs_fire"] == card.costs_fire
        assert d["costs_spirits"] == card.costs_spirits
        assert d["has_fire"] == card.has_fire
        assert d["has_spirits"] == card.has_spirits

    def test_serialise_no_skills_gives_empty_list(self):
        d = serialise_card_placement(0, self._plain_card())
        assert d["skills"] == []

    def test_serialise_skills_as_class_names(self):
        d = serialise_card_placement(0, self._skilled_card())
        assert set(d["skills"]) == {"Spines", "Shield"}

    def test_deserialise_plain_card_round_trip(self):
        card = self._plain_card()
        data = serialise_card_placement(0, card)
        restored = deserialise_card(data)
        assert restored.name == card.name
        assert restored.power == card.power
        assert restored.health == card.health
        assert restored.costs_fire == card.costs_fire
        assert restored.costs_spirits == card.costs_spirits
        assert restored.has_fire == card.has_fire
        assert restored.has_spirits == card.has_spirits
        assert restored.skills.count() == 0

    def test_deserialise_skilled_card_round_trip(self):
        card = self._skilled_card()
        data = serialise_card_placement(0, card)
        restored = deserialise_card(data)
        assert skills.Spines in restored.skills
        assert skills.Shield in restored.skills
        assert restored.skills.count() == 2

    def test_deserialise_unknown_skill_is_ignored(self):
        """A client receiving data with an unknown skill name must not crash."""
        card = self._plain_card()
        data = serialise_card_placement(0, card)
        data["skills"] = ["NonExistentSkill", "Spines"]
        restored = deserialise_card(data)
        assert skills.Spines in restored.skills
        assert restored.skills.count() == 1

    def test_full_wire_round_trip_via_sockets(self):
        """Serialise → fight_cards msg → send over socket → recv → deserialise."""
        cli, srv = make_loopback_pair()
        card = self._skilled_card()
        payload = [serialise_card_placement(3, card)]
        msg = make_fight_cards_msg(payload)

        t = threading.Thread(target=send_message, args=(cli, msg), daemon=True)
        t.start()
        received = recv_message(srv)
        t.join(timeout=2)

        assert received["type"] == MSG_FIGHT_CARDS
        restored = deserialise_card(received["cards"][0])
        assert restored.name == card.name
        assert received["cards"][0]["slot"] == 3
        assert skills.Spines in restored.skills
        cli.close()
        srv.close()

    def test_empty_cards_list_round_trip(self):
        """A round where the player places no cards must still send a valid message."""
        cli, srv = make_loopback_pair()
        msg = make_fight_cards_msg([])
        t = threading.Thread(target=send_message, args=(cli, msg), daemon=True)
        t.start()
        received = recv_message(srv)
        t.join(timeout=2)
        assert received["type"] == MSG_FIGHT_CARDS
        assert received["cards"] == []
        cli.close()
        srv.close()
