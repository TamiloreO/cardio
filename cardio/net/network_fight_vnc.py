"""cardio.net.network_fight_vnc — Networked fight controller.

``NetworkFightVnC`` is a thin subclass of the normal
:class:`~cardio.tui.locations.fightview.TUIFightVnC` that replaces the single-player
computer-strategy round loop with a synchronized two-player exchange over TCP.

Round synchronisation protocol
--------------------------------
Both peers share the same grid layout (3 lines × grid_width slots).  Each peer's own
cards live in line 2 (human line) on *their* local machine.  Each peer's opponent
cards live in lines 0/1 (computer lines) on *their* local machine.

Within every round the following sequence is enforced:

1. **Human plays cards** (unchanged from single-player).
   After the human presses C to end their turn, the controller collects every card that
   was newly placed in line 2 during this turn.

2. **Send** the local line-2 placements to the opponent as a ``FIGHT_CARDS`` message.

3. **Receive** the opponent's ``FIGHT_CARDS`` message via
   :meth:`~cardio.net.network_strategy.RemoteStrategy.fetch_remote_cards`.
   The remote strategy stores these placements and will inject them into line 1 when
   ``play_cards()`` is called momentarily.

4. **Activate** – the normal fight activation loop runs.  Because both sides sent their
   placements in step 2 and received the opponent's placements in step 3, both local
   grids are now in an equivalent state (mirrored), so damage computations on both
   machines agree without any further synchronisation.

5. At the end of the fight each side sends ``FIGHT_DONE`` and waits for the peer's
   ``FIGHT_DONE`` before returning, so neither machine closes the socket prematurely.

Card tracking
-------------
To know *which* cards are new in line 2 each round (step 1), the controller snapshots
line 2 at the *start* of the human-play phase and diffs it against line 2 at the *end*.
Only newly appearing cards are transmitted; cards that were already present in a prior
round are not re-sent.

Disconnection handling
----------------------
If the remote peer disconnects (socket closed, network error), a
:class:`NetworkDisconnectedError` is raised.  The caller (play.py) catches this and
returns the player to the main menu with an appropriate message.
"""

from __future__ import annotations

import logging
import socket
from typing import Dict, List, Optional, Set

from cardio import FightCard, Grid, GridPos
from cardio.tui.locations.fightview import TUIFightVnC
from cardio.tui.utils import dPos, show_text
from cardio.tui.constants import Color
from cardio.net.network_strategy import RemoteStrategy
from cardio.net.protocol import (
    send_message,
    recv_message,
    make_fight_cards_msg,
    make_fight_done_msg,
    serialise_card_placement,
    MSG_FIGHT_DONE,
)

log = logging.getLogger(__name__)

# Line index for each player on the local grid.
_HUMAN_LINE = 2
_COMPUTER_LINE = 1  # Where remote-player cards land (skipping the prep line).


class NetworkDisconnectedError(Exception):
    """Raised when the remote peer disconnects during a multiplayer fight."""

    pass



class NetworkFightVnC(TUIFightVnC):
    """TUI fight view-and-controller for LAN multiplayer.

    Drop-in replacement for :class:`~cardio.tui.locations.fightview.TUIFightVnC` when
    playing against a remote human.  Everything that touches the *visual* layer
    (animations, key-handling, screen drawing) is inherited unchanged.  Only the
    round-logic hook :meth:`_handle_round_of_fight` is overridden.

    Parameters
    ----------
    sock:
        Connected, blocking TCP socket to the remote peer.  This class *writes* to it;
        :class:`~cardio.net.network_strategy.RemoteStrategy` *reads* from it.
    All other parameters are forwarded to ``TUIFightVnC`` / ``FightVnC``.
    """

    def __init__(self, sock: socket.socket, *args, **kwargs) -> None:
        # Build a RemoteStrategy placeholder so FightVnC.__init__ receives a valid
        # strategy object.  The actual grid reference will be set after super().__init__
        # because TUIFightVnC.__init__ -> FightVnC.__init__ creates self.grid.
        #
        # We pass a sentinel Grid here; RemoteStrategy.grid is replaced in __init__
        # with self.grid (the real grid) right after the super call.
        sentinel_grid = Grid(4)
        remote_strategy = RemoteStrategy(sock=sock, grid=sentinel_grid)
        kwargs["computerstrategy"] = remote_strategy
        super().__init__(*args, **kwargs)

        # Now replace sentinel with the real grid that FightVnC built.
        self._remote_strategy = remote_strategy
        self._remote_strategy.grid = self.grid

        self._sock = sock
        # Snapshot of which FightCard *objects* were in line 2 at the start of the
        # current round's human-play phase.  We diff against this to find new cards.
        self._line2_snapshot: Set[int] = set()  # ids of FightCard objects

    # ── overridden round hook ──────────────────────────────────────────────────

    def _show_turn_indicator(self, whose_turn: str) -> None:
        """Display a turn indicator at the bottom of the screen."""
        indicator_y = self.screen.height - 2
        cx = self.screen.width // 2
        # Clear the line first.
        self.screen.clear_buffer(0, 0, 0, x=0, y=indicator_y, w=self.screen.width, h=1)
        if whose_turn == "your":
            msg = "⚔  YOUR TURN – Play cards, then press C to end turn  ⚔"
            color = Color.GREEN
        else:
            msg = "⏳  WAITING FOR OPPONENT...  ⏳"
            color = Color.YELLOW
        show_text(self.screen, dPos(cx - len(msg) // 2, indicator_y), msg, color=color)
        self.screen.refresh()

    def _handle_round_of_fight(self) -> None:
        """Networked round: send local placements, receive remote placements, activate.

        The activation logic (lines activating, damage, skills) runs identically to the
        single-player path because it is fully deterministic given the grid state.
        """
        log.debug("=== Network round %d start ===", self.round_num)
        from cardio.fightvnc import EndOfFightException
        from cardio.states_logger import StatesLogger

        self.stateslogger.log_current_state()
        self.decks.log()

        # ── step 1: show opponent's previously received cards (already in grid) ──
        # The remote strategy already placed cards from the *previous* round's exchange
        # into line 1 via play_cards().  We animate them appearing from off-screen so
        # the local player can see what the opponent played.
        for slot, card in self._iter_line(_COMPUTER_LINE):
            if id(card) in self._new_remote_card_ids:
                self.show_computer_plays_card(card, GridPos(_COMPUTER_LINE, slot))
        self._new_remote_card_ids = set()

        # ── step 2: snapshot line 2 before human plays ────────────────────────
        self._line2_snapshot = {
            id(card)
            for card in self.grid.lines[_HUMAN_LINE]
            if card is not None
        }

        # ── step 3: human draws a card ─────────────────────────────────────────
        deck = self.handle_human_choose_deck_to_draw_from()
        if deck is not None:
            card = deck.draw_card()
            self.show_human_draws_new_card(self.decks.hand, card, deck)
            self.decks.hand.add_card(card)

        # ── step 4: human plays cards (normal single-player interaction) ───────
        self._show_turn_indicator("your")
        self.handle_human_plays_cards(place_card_callback=self._place_card)

        # ── step 5: collect newly placed cards from line 2 ────────────────────
        new_cards = self._collect_new_line2_cards()

        # ── step 6: send our placements to the opponent ────────────────────────
        payload = [serialise_card_placement(slot, card) for slot, card in new_cards]
        try:
            send_message(self._sock, make_fight_cards_msg(payload))
        except ConnectionError as exc:
            log.error("Failed to send cards to opponent: %s", exc)
            raise NetworkDisconnectedError("Lost connection to opponent.") from exc
        log.debug("Sent %d card placement(s) to opponent.", len(payload))

        # ── step 7: receive the opponent's placements ──────────────────────────
        # This blocks until the remote side sends its FIGHT_CARDS message.
        self._show_turn_indicator("opponent")
        try:
            self._remote_strategy.fetch_remote_cards()
        except ConnectionError as exc:
            log.error("Failed to receive cards from opponent: %s", exc)
            raise NetworkDisconnectedError("Lost connection to opponent.") from exc
        # Inject received cards into the grid (line 1) via the normal play_cards path.
        self._remote_strategy.play_cards(self.round_num)
        # Track which ids are new so we can animate them at the top of the next round.
        self._new_remote_card_ids = {
            id(card)
            for card in self.grid.lines[_COMPUTER_LINE]
            if card is not None
        }

        self.decks.log()
        self.grid.log()

        # ── step 8: activate all cards (identical to single-player) ───────────
        for linei in [_HUMAN_LINE, _COMPUTER_LINE, 0]:
            for card in (c for c in self.grid.lines[linei] if c):
                if linei == 0:
                    if not card.prepare():
                        continue
                card.attack(self.grid.get_opposing_card(card))
            self._check_for_end_of_fight()

        self.damagestate.add_to_history(self.round_num)
        self._check_for_end_of_fight()

        # ── step 9: post-round skill hooks ─────────────────────────────────────
        cards = [card for line in reversed(self.grid.lines) for card in line if card]
        cards += (
            self.decks.draw.cards + self.decks.hand.cards + self.decks.hamster.cards
        )
        for card in cards:
            card.skills.call("post_round", card)

        self.grid.log()
        log.debug("=== Network round %d end ===", self.round_num)


    def handle_fight(self) -> None:
        """Override to initialise tracking state before delegating to parent."""
        # Initialise the set that _handle_round_of_fight reads on the very first round.
        self._new_remote_card_ids: Set[int] = set()
        # Run the normal fight loop (which calls our overridden _handle_round_of_fight).
        # NetworkDisconnectedError may propagate up from _handle_round_of_fight.
        super().handle_fight()
        # ── fight is over: exchange FIGHT_DONE so both sides close cleanly ────
        try:
            send_message(self._sock, make_fight_done_msg())
            msg = recv_message(self._sock)
            if msg.get("type") != MSG_FIGHT_DONE:
                log.warning(
                    "Expected FIGHT_DONE from peer, got %r", msg.get("type")
                )
        except ConnectionError as exc:
            log.warning("Could not exchange FIGHT_DONE: %s", exc)
            # Don't raise here - fight is already over, just log and continue.


    # ── helpers ────────────────────────────────────────────────────────────────

    def _collect_new_line2_cards(self) -> List[tuple]:
        """Return ``(slot, card)`` pairs for cards that appeared in line 2 this round.

        A card is considered "new" if its object identity was not in the snapshot taken
        before the human-play phase.  This correctly handles cards added by skills such
        as Fertility (which creates copies).
        """
        new: List[tuple] = []
        for slot, card in self._iter_line(_HUMAN_LINE):
            if id(card) not in self._line2_snapshot:
                new.append((slot, card))
        return new

    def _iter_line(self, linei: int):
        """Yield ``(slot, card)`` for every non-empty cell in *linei*."""
        for slot, card in enumerate(self.grid.lines[linei]):
            if card is not None:
                yield slot, card
