"""Multiplayer fight controller handling game synchronization between two human players."""

import logging
import threading
import time
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Any

from cardio import FightCard, Deck, FightDecks, Grid, GridPos
from cardio.human_player import HumanPlayer
from cardio.placement_manager import PlacementManager
from cardio.agent_damage_state import AgentDamageState
from cardio.whichplayer import WhichPlayer
from cardio.states_logger import StatesLogger

from .network import MessageType, MultiplayerClient, MultiplayerServer, NetworkMessage


@dataclass
class PlayerAction:
    """Represents an action taken by a player."""

    action_type: str
    data: Dict[str, Any]


class MultiplayerFightVnC:
    """Fight controller for multiplayer games.

    In multiplayer, both players share the same grid, taking turns.
    Player 1 controls the "human" side (lines 2-3), Player 2 controls the "computer" side
    (lines 0-1). The roles can swap each round or stay fixed based on game mode.
    """

    def __init__(
        self,
        grid: Grid,
        local_player: HumanPlayer,
        remote_player_name: str,
        is_host: bool,
        server: Optional[MultiplayerServer] = None,
        client: Optional[MultiplayerClient] = None,
    ):
        self.grid = grid
        self.local_player = local_player
        self.remote_player_name = remote_player_name
        self.is_host = is_host
        self.server = server
        self.client = client

        self.damagestate = AgentDamageState()
        self.stateslogger = StatesLogger(self)
        FightCard.init_fight(self, self.grid)

        # Which side of the grid the local player controls
        # Host plays "human" side (line 2), guest plays "computer" side (line 1)
        self.local_is_human_side = is_host

        self.round_num = 0
        self.decks = FightDecks()
        self.waiting_for_remote = False
        self.remote_action: Optional[PlayerAction] = None
        self._action_lock = threading.Lock()
        self._action_event = threading.Event()

        self._setup_network_handlers()

    def _setup_network_handlers(self) -> None:
        """Setup handlers for network messages."""
        if self.server:
            self.server.register_handler(
                MessageType.PLAYER_ACTION, self._handle_remote_action_server
            )
            self.server.register_handler(
                MessageType.TURN_END, self._handle_turn_end_server
            )
        if self.client:
            self.client.register_handler(
                MessageType.PLAYER_ACTION, self._handle_remote_action_client
            )
            self.client.register_handler(
                MessageType.TURN_END, self._handle_turn_end_client
            )
            self.client.register_handler(
                MessageType.GAME_STATE, self._handle_game_state
            )

    def _handle_remote_action_server(
        self, conn, message: NetworkMessage
    ) -> None:
        """Handle action from remote player (server-side)."""
        self._process_remote_action(message)
        # Relay to all other clients if needed
        if self.server:
            self.server.broadcast(message, exclude=conn)

    def _handle_remote_action_client(self, message: NetworkMessage) -> None:
        """Handle action from remote player (client-side)."""
        self._process_remote_action(message)

    def _process_remote_action(self, message: NetworkMessage) -> None:
        """Process an action received from the remote player."""
        with self._action_lock:
            self.remote_action = PlayerAction(
                action_type=message.data.get("action_type", ""),
                data=message.data.get("data", {}),
            )
        self._action_event.set()

    def _handle_turn_end_server(self, conn, message: NetworkMessage) -> None:
        """Handle turn end from remote player (server-side)."""
        self._action_event.set()
        if self.server:
            self.server.broadcast(message, exclude=conn)

    def _handle_turn_end_client(self, message: NetworkMessage) -> None:
        """Handle turn end from server."""
        self._action_event.set()

    def _handle_game_state(self, message: NetworkMessage) -> None:
        """Handle full game state sync from server."""
        # Sync grid state, damage state, etc.
        grid_data = message.data.get("grid", [])
        damage_data = message.data.get("damage", {})
        # Apply state... (simplified for now)

    def _send_action(self, action_type: str, data: Dict[str, Any]) -> None:
        """Send an action to the remote player."""
        message = NetworkMessage(
            type=MessageType.PLAYER_ACTION,
            data={"action_type": action_type, "data": data},
        )
        if self.server:
            self.server.broadcast(message)
        elif self.client:
            self.client.send(message)

    def _send_turn_end(self) -> None:
        """Signal end of turn to remote player."""
        message = NetworkMessage(type=MessageType.TURN_END, data={})
        if self.server:
            self.server.broadcast(message)
        elif self.client:
            self.client.send(message)

    def _wait_for_remote_action(self, timeout: float = 60.0) -> Optional[PlayerAction]:
        """Wait for the remote player's action."""
        self._action_event.clear()
        self.waiting_for_remote = True

        if self._action_event.wait(timeout):
            with self._action_lock:
                action = self.remote_action
                self.remote_action = None
            self.waiting_for_remote = False
            return action

        self.waiting_for_remote = False
        return None

    # --- Methods mirroring FightVnC interface ---

    def card_died(self, card: FightCard, pos: GridPos) -> None:
        pass

    def card_lost_health(self, card: FightCard) -> None:
        pass

    def show_card_getting_attacked(
        self, target: FightCard, attacker: FightCard
    ) -> None:
        pass

    def show_card_activate(self, card: FightCard) -> None:
        pass

    def show_card_prepare(self, card: FightCard) -> None:
        pass

    def show_card_deactivate(self, card: FightCard) -> None:
        pass

    def redraw_view(self) -> None:
        pass

    def fight_ends(self, msg: str) -> None:
        pass

    def show_human_draws_new_card(
        self, draw_to: Deck, card: FightCard, draw_from: Deck
    ) -> None:
        pass

    def show_human_receives_card_from_grid(
        self, card: FightCard, from_slot: int
    ) -> None:
        pass

    def show_computer_plays_card(self, card: FightCard, to: GridPos) -> None:
        pass

    def show_human_places_card(
        self, card: FightCard, from_slot: int, to_slot: int
    ) -> None:
        pass

    def handle_human_choose_deck_to_draw_from(self) -> Optional[Deck]:
        return None

    def handle_human_plays_cards(self, place_card_callback: Callable) -> None:
        pass

    def handle_agent_damage(self, to_: WhichPlayer, howmuch: int) -> None:
        self.damagestate.apply_damage(to_, howmuch)
        self.redraw_view()

    # --- Multiplayer-specific methods ---

    def sync_card_placement(
        self, card_name: str, from_slot: int, to_slot: int
    ) -> None:
        """Send card placement to remote player."""
        self._send_action(
            "place_card",
            {"card_name": card_name, "from_slot": from_slot, "to_slot": to_slot},
        )

    def sync_deck_draw(self, deck_name: str, card_name: str) -> None:
        """Send deck draw action to remote player."""
        self._send_action(
            "deck_draw", {"deck_name": deck_name, "card_name": card_name}
        )

    def get_local_line(self) -> int:
        """Get the grid line that the local player controls."""
        return 2 if self.local_is_human_side else 1

    def get_remote_line(self) -> int:
        """Get the grid line that the remote player controls."""
        return 1 if self.local_is_human_side else 2

    def is_local_turn(self) -> bool:
        """Check if it's the local player's turn."""
        # In multiplayer, both players act simultaneously in their respective lines
        return True

    def handle_multiplayer_fight(self) -> None:
        """Main fight loop for multiplayer games."""
        logging.info("Starting multiplayer fight")

        # Set up decks
        self.decks = FightDecks()
        self.decks.draw.cards = FightCard.from_cards(self.local_player.deck.cards)
        hamster_cards = [
            self.local_player.hamster_blueprint.instantiate() for _ in range(10)
        ]
        self.decks.hamster.cards = FightCard.from_cards(hamster_cards)
        self.decks.draw.shuffle()

        # Initialize skills
        for card in self.decks.draw.cards + self.decks.hamster.cards:
            card.skills.call("pre_fight", card)

        self.redraw_view()

        # Draw initial cards
        for _ in range(3):
            if not self.decks.draw.is_empty():
                card = self.decks.draw.draw_card()
                self.show_human_draws_new_card(self.decks.hand, card, self.decks.draw)
                self.decks.hand.add_card(card)

        # Main fight loop
        self.round_num = 0
        winner = None

        while True:
            try:
                self._handle_multiplayer_round()
            except EndOfMultiplayerFight as exc:
                winner = exc.winner
                break
            self.round_num += 1

        # Handle end of fight
        if winner == ("human" if self.local_is_human_side else "computer"):
            self.local_player.lives -= 1
            if self.local_player.lives > 0:
                self.fight_ends(f"You lose! {self.local_player.lives} lives left.")
            else:
                self.fight_ends("You lose! No lives left.")
        else:
            gems = self.damagestate.get_overflow()
            self.local_player.gems += gems
            self.fight_ends(f"You win! Gained {gems} gems.")

    def _handle_multiplayer_round(self) -> None:
        """Handle a single round of multiplayer fight."""
        logging.debug("Multiplayer round %d", self.round_num)

        # Both players draw and play cards on their respective sides
        # Then cards activate from both sides

        # Let local player draw
        deck = self.handle_human_choose_deck_to_draw_from()
        if deck is not None:
            card = deck.draw_card()
            self.show_human_draws_new_card(self.decks.hand, card, deck)
            self.decks.hand.add_card(card)
            self.sync_deck_draw(deck.name, card.name)

        # Let local player play cards
        self.handle_human_plays_cards(place_card_callback=self._place_card_multiplayer)

        # Signal turn end and wait for remote
        self._send_turn_end()
        self._wait_for_remote_action(timeout=120.0)

        # Activate cards
        lines_order = [2, 1, 0] if self.local_is_human_side else [0, 1, 2]
        for linei in lines_order:
            for card in (c for c in self.grid.lines[linei] if c):
                if linei == 0:
                    if not card.prepare():
                        continue
                card.attack(self.grid.get_opposing_card(card))
            self._check_for_end_of_fight()

        self.damagestate.add_to_history(self.round_num)
        self._check_for_end_of_fight()

    def _place_card_multiplayer(self, pmgr: PlacementManager, from_slot: int) -> None:
        """Place a card and sync with remote player."""
        # Update model
        for sacrifice_pos in pmgr.get_marked_positions():
            card = self.grid.get_card(sacrifice_pos)
            if card:
                card.sacrifice()
        self.local_player.spirits -= pmgr.target_card.costs_spirits
        self.grid.set_card(pmgr.placement_position, pmgr.target_card)

        # Update view
        to_slot = pmgr.get_placement_position().slot
        self.show_human_places_card(pmgr.target_card, from_slot, to_slot)
        self.decks.hand.pick_card(from_slot)

        # Sync with remote
        self.sync_card_placement(pmgr.target_card.name, from_slot, to_slot)

        self.redraw_view()

    def _check_for_end_of_fight(self) -> None:
        """Check if the fight should end."""
        winner = self.damagestate.who_won()
        if winner:
            raise EndOfMultiplayerFight(winner)


class EndOfMultiplayerFight(Exception):
    """Raised when a multiplayer fight ends."""

    def __init__(self, winner: WhichPlayer):
        self.winner = winner
