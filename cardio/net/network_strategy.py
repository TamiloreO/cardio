"""cardio.net.network_strategy — Remote-player card strategy.

In a normal single-player fight the computer opponent is driven by a
:class:`~cardio.computer_strategies.ComputerStrategy` which deterministically picks
cards from its own deck and places them onto the grid.

In multiplayer the *opponent* is a remote human who makes those placement decisions
themselves on their own machine.  ``RemoteStrategy`` replaces the computer strategy on
each local machine: instead of generating cards algorithmically,
:meth:`~RemoteStrategy.cards_to_be_played` blocks on the network socket until the
opponent's round-card message arrives, then returns the decoded placements so they can
be fed into the normal fight pipeline unchanged.

Wire format
-----------
The message received must be a ``FIGHT_CARDS`` envelope (see
:mod:`cardio.net.protocol`).  The ``cards`` list is decoded with
:func:`~cardio.net.protocol.deserialise_card` and the resulting ``Card`` objects are
wrapped in :class:`~cardio.fightcard.FightCard` instances before being returned.

Placement line
--------------
In the normal computer strategy cards land on line 0 (prep) first and are moved to
line 1 by :meth:`~cardio.fightcard.FightCard.prepare` during the activation phase.
For the remote opponent's cards we skip the prep step and place directly into line 1.
The prep-line mechanism exists to create a one-round delay for the computer; we do not
want that delay in a human-vs-human fight because both players place simultaneously and
would see each other's cards arrive one round late.  By using line 1 directly the
opponent's cards appear immediately, which is the visually correct and strategically
fair behaviour.
"""

from __future__ import annotations

import logging
import socket
from typing import List, TYPE_CHECKING

from cardio.computer_strategies import ComputerStrategy
from cardio import Grid, GridPos, GridPosAndCard, FightCard
from cardio.net.protocol import (
    recv_message,
    MSG_FIGHT_CARDS,
    deserialise_card,
)

if TYPE_CHECKING:
    pass

log = logging.getLogger(__name__)


class RemoteStrategy(ComputerStrategy):
    """A computer strategy that receives card placements from a remote peer.

    Parameters
    ----------
    sock:
        A connected, blocking TCP socket shared with the network fight controller.
        ``RemoteStrategy`` only *reads* from this socket;
        :class:`~cardio.net.network_fight_vnc.NetworkFightVnC` is responsible for
        writing.
    grid:
        The fight grid (forwarded to the parent :class:`ComputerStrategy`).
    """

    def __init__(self, sock: socket.socket, grid: Grid) -> None:
        super().__init__(grid=grid)
        self._sock = sock
        # Buffer of placements received for the current round.
        # Populated by _fetch_remote_cards(); cleared in cards_to_be_played().
        self._pending: List[GridPosAndCard] = []

    # ── public API ─────────────────────────────────────────────────────────────

    def fetch_remote_cards(self) -> None:
        """Block until the opponent's FIGHT_CARDS message for this round arrives.

        Called by :class:`~cardio.net.network_fight_vnc.NetworkFightVnC` *before* the
        activation phase so that the opponent's placements are in the grid in time for
        the attack loop.  Stores decoded placements in ``_pending``.
        """
        log.debug("RemoteStrategy: waiting for opponent's cards …")
        msg = recv_message(self._sock)
        if msg.get("type") != MSG_FIGHT_CARDS:
            log.warning(
                "RemoteStrategy: unexpected message type %r (expected %r)",
                msg.get("type"),
                MSG_FIGHT_CARDS,
            )
            self._pending = []
            return

        placements: List[GridPosAndCard] = []
        for entry in msg.get("cards", []):
            slot = int(entry["slot"])
            card = deserialise_card(entry)
            fc = FightCard.from_card(card)
            # Place directly into line 1 (active fight line), skipping the prep-line
            # delay that the normal computer strategy uses.
            placements.append(GridPosAndCard(GridPos(1, slot), fc))
            log.debug(
                "RemoteStrategy: received card %r for slot %d", card.name, slot
            )

        self._pending = placements

    def cards_to_be_played(self, round_number: int) -> List[GridPosAndCard]:
        """Return the placements fetched from the remote peer and clear the buffer.

        This method is called by :meth:`~cardio.computer_strategies.ComputerStrategy.play_cards`
        which is in turn called by the fight loop.  By the time this method is called,
        :meth:`fetch_remote_cards` will already have populated ``_pending``.
        """
        placements = self._pending
        self._pending = []
        return placements
