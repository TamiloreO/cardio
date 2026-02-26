"""TUI Fight View for Multiplayer mode.

Extends the regular TUIFightVnC with multiplayer-specific UI elements
and synchronization feedback.
"""

import threading
import time
from typing import Callable, Literal, Optional

from asciimatics.screen import Screen

from cardio import FightCard, Deck, Grid, GridPos
from cardio.human_player import HumanPlayer
from cardio.placement_manager import (
    PlacementManager,
    PlacementAbortedException,
    PlacementNotPossibleException,
)
from cardio.multiplayer.network import (
    MessageType,
    MultiplayerClient,
    MultiplayerServer,
    NetworkMessage,
)
from cardio.multiplayer.multiplayer_fight import MultiplayerFightVnC

from ..card_primitives import (
    VisualState,
    show_card,
    activate_card,
    burn_card,
    move_card,
    redraw_card,
    shake_card,
    clear_card,
    flash_card,
)
from ..decks_primitives import (
    show_card_to_handdeck,
    show_drawdeck_cursor,
    show_drawdecks,
    redraw_handdeck,
)
from ..grid_primitives import show_empty_grid, show_slot_in_grid
from ..agent_primitives import StateWidget
from ..utils import show_screen_resolution, get_keycode, show_text, dPos
from ..constants import Color
from ..tuibase import TUIBaseMixin


class TUIMultiplayerFightVnC(TUIBaseMixin, MultiplayerFightVnC):
    """TUI implementation of multiplayer fight."""

    INFO_POS = dPos(120, 2)
    STATUS_POS = dPos(120, 15)

    def __init__(
        self,
        grid: Grid,
        local_player: HumanPlayer,
        remote_player_name: str,
        is_host: bool,
        server: Optional[MultiplayerServer] = None,
        client: Optional[MultiplayerClient] = None,
        debug: bool = False,
        description: Optional[str] = None,
        *args,
        **kwargs,
    ) -> None:
        # Initialize TUIBaseMixin first
        TUIBaseMixin.__init__(self, description=description, debug=debug)

        # Then initialize MultiplayerFightVnC
        MultiplayerFightVnC.__init__(
            self,
            grid=grid,
            local_player=local_player,
            remote_player_name=remote_player_name,
            is_host=is_host,
            server=server,
            client=client,
        )

        if self.debug:
            show_screen_resolution(self.screen)

        self.state_widget = StateWidget(
            self.screen, self.grid.width, self.damagestate, self.local_player
        )

        # Status message for multiplayer state
        self.status_message = ""
        self._status_lock = threading.Lock()

    def set_status(self, message: str) -> None:
        """Set the status message shown during multiplayer."""
        with self._status_lock:
            self.status_message = message
        self.redraw_view()

    def redraw_view(
        self,
        cursor: Optional[GridPos] = None,
        drawdeck_cursor: Optional[Literal[0, 1]] = None,
        pmgr: Optional[PlacementManager] = None,
    ) -> None:
        """Redraw the entire game view."""
        self.screen.clear_buffer(0, 0, 0)
        show_empty_grid(self.screen, self.grid.width)

        # Draw all cards on the grid
        for linei in range(len(self.grid.lines)):
            for sloti in range(self.grid.width):
                pos = GridPos(linei, sloti)
                card = self.grid.get_card(pos)
                if card is not None:
                    redraw_card(self.screen, card, pos)

        # Draw hand and draw decks
        redraw_handdeck(self.screen, self.decks.hand, 0)
        show_drawdecks(self.screen, self.decks.draw, self.decks.hamster)

        # Draw marked positions (for card placement)
        for pos in pmgr.marked_positions if pmgr else []:
            show_card(self.screen, None, pos, VisualState.MARKED)

        # Draw cursors
        if cursor:
            if pmgr and pmgr.ready_to_pick():
                state = VisualState.READY
            else:
                state = VisualState.CURSOR
            show_card(self.screen, None, cursor, state)

        if drawdeck_cursor is not None:
            show_drawdeck_cursor(self.screen, drawdeck_cursor)

        # Draw player info
        self.state_widget.show_all()

        # Draw multiplayer-specific info
        self._draw_multiplayer_info()

        if self.debug:
            show_screen_resolution(self.screen)

        self.screen.refresh()

    def _draw_multiplayer_info(self) -> None:
        """Draw multiplayer-specific information."""
        # Player names and roles
        show_text(
            self.screen,
            self.INFO_POS,
            f"You: {self.local_player.name}",
            color=Color.CYAN,
        )
        show_text(
            self.screen,
            self.INFO_POS + (0, 1),
            f"Opponent: {self.remote_player_name}",
            color=Color.MAGENTA,
        )

        # Role indicator
        role = "Defender" if self.local_is_human_side else "Attacker"
        show_text(
            self.screen,
            self.INFO_POS + (0, 3),
            f"Your role: {role}",
            color=Color.WHITE,
        )

        # Round number
        show_text(
            self.screen,
            self.INFO_POS + (0, 5),
            f"Round: {self.round_num}",
            color=Color.WHITE,
        )

        # Waiting status
        with self._status_lock:
            status = self.status_message

        if status:
            show_text(self.screen, self.STATUS_POS, status, color=Color.YELLOW)

        if self.waiting_for_remote:
            show_text(
                self.screen,
                self.STATUS_POS + (0, 2),
                "Waiting for opponent...",
                color=Color.GRAY,
            )

    def card_died(self, card: FightCard, pos: GridPos) -> None:
        burn_card(self.screen, pos)
        show_slot_in_grid(self.screen, pos)
        self.redraw_view()

    def card_lost_health(self, card: FightCard) -> None:
        self.redraw_view()

    def show_card_getting_attacked(
        self, target: FightCard, attacker: FightCard
    ) -> None:
        pos = target.get_grid_pos()
        shake_card(self.screen, target, pos, "h")

    def show_card_activate(self, card: FightCard) -> None:
        pos = card.get_grid_pos()
        activate_card(self.screen, card, pos)

    def show_card_prepare(self, card: FightCard) -> None:
        pos = card.get_grid_pos()
        assert pos.line == 0, "Calling prepare on card that is not in prep line"
        clear_card(self.screen, pos)
        show_slot_in_grid(self.screen, pos)
        move_card(
            self.screen, card, from_=GridPos(0, pos.slot), to=GridPos(1, pos.slot)
        )

    def show_card_deactivate(self, pos: GridPos) -> None:
        self.redraw_view()

    def fight_ends(self, msg: str) -> None:
        self.message(msg)

    def show_computer_plays_card(self, card: FightCard, to: GridPos) -> None:
        """Show opponent playing a card."""
        move_card(
            self.screen,
            card,
            from_=GridPos(-2, self.grid.width // 2),
            to=to,
            steps=5,
        )

    def show_human_places_card(
        self, card: FightCard, from_slot: int, to_slot: int
    ) -> None:
        move_card(
            self.screen, card, from_=GridPos(4, from_slot), to=GridPos(2, to_slot)
        )

    def show_human_receives_card_from_grid(
        self, card: FightCard, from_slot: int
    ) -> None:
        move_card(
            self.screen,
            card,
            GridPos(2, from_slot),
            GridPos(4, self.decks.hand.size() - 1),
        )

    def handle_human_choose_deck_to_draw_from(self) -> Optional[Deck]:
        """Human player draws a card from one of the draw decks."""
        if not self.decks.draw.is_empty():
            cursor = 0
        elif not self.decks.hamster.is_empty():
            cursor = 1
        else:
            return None

        while True:
            self.redraw_view(drawdeck_cursor=cursor)
            keycode = get_keycode(self.screen)
            if keycode == Screen.KEY_LEFT and not self.decks.draw.is_empty():
                cursor = 0
            elif keycode == Screen.KEY_RIGHT and not self.decks.hamster.is_empty():
                cursor = 1
            elif keycode in (Screen.KEY_UP, 13):
                return self.decks.draw if cursor == 0 else self.decks.hamster

    def _handle_card_placement_interaction(self, pmgr: PlacementManager) -> None:
        """Handle the card placement interaction."""
        if not pmgr.is_placeable():
            raise PlacementNotPossibleException

        cursor = 0
        while not pmgr.ready_to_place():
            cursor_pos = GridPos(2, cursor)
            self.redraw_view(cursor=cursor_pos, pmgr=pmgr)

            keycode = get_keycode(self.screen)
            if keycode == Screen.KEY_LEFT:
                cursor = max(0, cursor - 1)
            elif keycode == Screen.KEY_RIGHT:
                cursor = min(self.grid.width - 1, cursor + 1)
            elif keycode in (Screen.KEY_DOWN, 13):
                if not pmgr.mark_unmark_or_pick(cursor_pos):
                    flash_card(self.screen, cursor_pos)
            elif keycode == Screen.KEY_ESCAPE:
                raise PlacementAbortedException

    def handle_human_plays_cards(self, place_card_callback: Callable) -> None:
        """Handle human player placing cards."""
        cursor = 0
        while True:
            keycode = get_keycode(self.screen)
            if keycode in (ord("i"), ord("I")):
                pass  # Inventory not implemented
            elif keycode in (ord("c"), ord("C")):
                break

            if self.decks.hand.is_empty():
                continue
            self.redraw_view(cursor=GridPos(4, cursor))

            if keycode == Screen.KEY_LEFT:
                cursor = max(0, cursor - 1)
            elif keycode == Screen.KEY_RIGHT:
                cursor = min(self.decks.hand.size() - 1, cursor + 1)
            elif keycode in (Screen.KEY_UP, 13):
                pmgr = PlacementManager(
                    grid=self.grid,
                    available_spirits=self.local_player.spirits,
                    target_card=self.decks.hand.cards[cursor],
                )
                try:
                    self._handle_card_placement_interaction(pmgr)
                except PlacementAbortedException:
                    pass
                except PlacementNotPossibleException:
                    flash_card(self.screen, GridPos(4, cursor))
                else:
                    place_card_callback(pmgr=pmgr, from_slot=cursor)
                    cursor = min(self.decks.hand.size() - 1, cursor)

    def show_human_draws_new_card(
        self, draw_to: Deck, card: FightCard, draw_from: Deck
    ) -> None:
        show_card_to_handdeck(self.screen, draw_to, card, draw_from)

    def handle_remote_card_played(
        self, card_name: str, from_slot: int, to_slot: int
    ) -> None:
        """Handle opponent playing a card (received over network)."""
        # Create a placeholder card for the animation
        # In a full implementation, we'd deserialize the actual card
        self.set_status(f"Opponent played: {card_name}")
        time.sleep(0.5)
        self.redraw_view()
