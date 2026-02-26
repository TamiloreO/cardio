"""cardio.net.protocol — Wire protocol for LAN multiplayer.

All traffic between host and guest is exchanged over a single TCP connection. Every
message is a self-delimiting JSON frame: a 4-byte big-endian unsigned integer length
prefix followed by exactly that many UTF-8 bytes of JSON.

Message types (the ``type`` key in every envelope):

``FIGHT_CARDS``
    Carries the list of cards that one player placed into their own line 2 during the
    current round.  The receiving side places those cards into its own line 1 (the
    "computer opponent" line), so each player sees its opponent's choices appear on the
    far side of the grid.

    Payload key ``cards``: list of objects with keys
        ``slot``        – integer column index (0 … grid_width-1)
        ``name``        – card name string
        ``power``       – integer
        ``health``      – integer
        ``costs_fire``  – integer
        ``costs_spirits`` – integer
        ``has_fire``    – integer
        ``has_spirits`` – integer
        ``skills``      – list of skill class-name strings (e.g. ``["Spines", "Shield"]``)

``FIGHT_DONE``
    Sent by both sides once their local fight loop ends.  Carries no additional payload.
    The recipient knows the remote side has also finished and can close the connection.
"""

from __future__ import annotations

import json
import socket
import struct
from typing import Any, Dict, List

# ── constants ─────────────────────────────────────────────────────────────────

# Header: 4 unsigned bytes, big-endian.
_HEADER_FMT = "!I"
_HEADER_SIZE = struct.calcsize(_HEADER_FMT)  # == 4

MSG_FIGHT_CARDS = "FIGHT_CARDS"
MSG_FIGHT_DONE = "FIGHT_DONE"


# ── low-level framing ──────────────────────────────────────────────────────────


def _send_raw(sock: socket.socket, data: bytes) -> None:
    """Send *data* over *sock* with a 4-byte length prefix.

    Raises ``ConnectionError`` on any socket error.
    """
    header = struct.pack(_HEADER_FMT, len(data))
    try:
        sock.sendall(header + data)
    except OSError as exc:
        raise ConnectionError(f"Network send failed: {exc}") from exc


def _recv_raw(sock: socket.socket) -> bytes:
    """Receive one complete framed message from *sock*.

    Blocks until all bytes of the message are available.
    Raises ``ConnectionError`` on any socket error or unexpected EOF.
    """
    header = _recv_exactly(sock, _HEADER_SIZE)
    (length,) = struct.unpack(_HEADER_FMT, header)
    return _recv_exactly(sock, length)


def _recv_exactly(sock: socket.socket, n: int) -> bytes:
    """Read exactly *n* bytes from *sock*, blocking as needed."""
    buf = bytearray()
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            raise ConnectionError("Remote side closed the connection unexpectedly.")
        buf.extend(chunk)
    return bytes(buf)


# ── high-level message helpers ─────────────────────────────────────────────────


def send_message(sock: socket.socket, msg: Dict[str, Any]) -> None:
    """Serialise *msg* to JSON and send it as a framed message."""
    _send_raw(sock, json.dumps(msg, ensure_ascii=False).encode("utf-8"))


def recv_message(sock: socket.socket) -> Dict[str, Any]:
    """Receive one framed message and deserialise it from JSON."""
    return json.loads(_recv_raw(sock).decode("utf-8"))


# ── typed message constructors ─────────────────────────────────────────────────


def make_fight_cards_msg(cards: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Build a ``FIGHT_CARDS`` message payload.

    ``cards`` is a list of dicts produced by :func:`serialise_card_placement`.
    """
    return {"type": MSG_FIGHT_CARDS, "cards": cards}


def make_fight_done_msg() -> Dict[str, Any]:
    """Build a ``FIGHT_DONE`` message."""
    return {"type": MSG_FIGHT_DONE}


# ── card serialisation ─────────────────────────────────────────────────────────


def serialise_card_placement(slot: int, card: Any) -> Dict[str, Any]:
    """Convert a ``(slot, card)`` pair into a JSON-safe dict.

    *card* is any object that exposes the standard ``Card`` attributes:
    ``name``, ``power``, ``health``, ``costs_fire``, ``costs_spirits``,
    ``has_fire``, ``has_spirits``, ``skills``.
    Skills are serialised as a list of class-name strings so they survive a round-trip
    through JSON without any cardio-specific JSON hooks.
    """
    return {
        "slot": slot,
        "name": card.name,
        "power": card.power,
        "health": card.health,
        "costs_fire": card.costs_fire,
        "costs_spirits": card.costs_spirits,
        "has_fire": card.has_fire,
        "has_spirits": card.has_spirits,
        "skills": [t.__name__ for t in card.skills.get_types()],
    }


def deserialise_card(data: Dict[str, Any]) -> Any:
    """Reconstruct a ``Card`` instance from the dict produced by
    :func:`serialise_card_placement`.

    Skill classes are looked up by name in :mod:`cardio.skills`.
    Unknown skill names are silently ignored so that an outdated client doesn't crash
    when connected to a host running a newer version.
    """
    from cardio.card import Card
    import cardio.skills as sk

    skill_types = []
    for name in data.get("skills", []):
        skill_cls = getattr(sk, name, None)
        if skill_cls is not None:
            skill_types.append(skill_cls)

    return Card(
        name=data["name"],
        power=data["power"],
        health=data["health"],
        costs_fire=data["costs_fire"],
        costs_spirits=data["costs_spirits"],
        has_fire=data["has_fire"],
        has_spirits=data["has_spirits"],
        skills=skill_types,
    )
