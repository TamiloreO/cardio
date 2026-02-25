from typing import List
from asciimatics.screen import Screen
from cardio import Card, Deck
from .utils import get_keycode, dPos, show_text
from .constants import Color, BOX_WIDTH, BOX_HEIGHT, BOX_PADDING_LEFT, BOX_PADDING_TOP
from .card_primitives import VisualState, show_card


class DeckExplorer:
    """A read-only view for exploring cards in a deck or collection."""

    def __init__(
        self, screen: Screen, deck: Deck, collection: Deck, title: str = "Deck Explorer"
    ) -> None:
        self.screen = screen
        self.deck = deck
        self.collection = collection
        self.title = title
        self.gross_width = BOX_WIDTH + BOX_PADDING_LEFT
        self.gross_height = BOX_HEIGHT + BOX_PADDING_TOP + 1
        self.cardsperline = (self.screen.width - 4) // self.gross_width
        self.header_height = 3
        self.showing_deck = True  # True = deck, False = collection

    def _get_current_cards(self) -> List[Card]:
        return self.deck.cards if self.showing_deck else self.collection.cards

    def _get_tab_label(self) -> str:
        deck_label = f"[D] Main Deck ({self.deck.size()})"
        collection_label = f"[C] Collection ({self.collection.size()})"
        if self.showing_deck:
            return f"${{{Color.YELLOW.value}}}{deck_label}${{7}}  |  {collection_label}"
        else:
            return f"{deck_label}  |  ${{{Color.YELLOW.value}}}{collection_label}${{7}}"

    def dpos_from_cardindex(self, idx: int) -> dPos:
        x = 2 + (idx % self.cardsperline) * self.gross_width
        y = self.header_height + (idx // self.cardsperline) * self.gross_height
        return dPos(x, y)

    def redraw(self, cursor: int = 0, scroll_offset: int = 0) -> None:
        self.screen.clear_buffer(0, 0, 0)

        show_text(self.screen, dPos(2, 0), self.title, color=Color.CYAN)
        show_text(self.screen, dPos(2, 1), self._get_tab_label())
        show_text(
            self.screen,
            dPos(self.screen.width - 30, 0),
            "ESC to close  |  D/C switch tabs",
            color=Color.GRAY,
        )

        cards = self._get_current_cards()
        if not cards:
            show_text(
                self.screen,
                dPos(2, self.header_height + 2),
                "No cards in this deck",
                color=Color.GRAY,
            )
        else:
            max_visible_rows = (self.screen.height - self.header_height - 2) // self.gross_height
            max_visible = max_visible_rows * self.cardsperline

            for i, card in enumerate(cards):
                if i < scroll_offset * self.cardsperline:
                    continue
                visible_idx = i - scroll_offset * self.cardsperline
                if visible_idx >= max_visible:
                    break

                pos = self.dpos_from_cardindex(visible_idx)
                if pos.y + BOX_HEIGHT > self.screen.height - 1:
                    break

                state = VisualState.CURSOR if i == cursor else VisualState.NORMAL
                show_card(self.screen, card, pos, state)

            total_rows = (len(cards) + self.cardsperline - 1) // self.cardsperline
            if total_rows > max_visible_rows:
                show_text(
                    self.screen,
                    dPos(2, self.screen.height - 1),
                    f"Showing rows {scroll_offset + 1}-{min(scroll_offset + max_visible_rows, total_rows)} of {total_rows} (↑↓ to scroll)",
                    color=Color.GRAY,
                )

        self.screen.refresh()

    def show(self) -> None:
        """Show the deck explorer and allow navigation. Press ESC to close."""
        cursor = 0
        scroll_offset = 0

        while True:
            cards = self._get_current_cards()
            max_visible_rows = (self.screen.height - self.header_height - 2) // self.gross_height

            # Adjust cursor if it's out of bounds after switching tabs
            if cards:
                cursor = min(cursor, len(cards) - 1)
            else:
                cursor = 0

            # Adjust scroll to keep cursor visible
            cursor_row = cursor // self.cardsperline
            if cursor_row < scroll_offset:
                scroll_offset = cursor_row
            elif cursor_row >= scroll_offset + max_visible_rows:
                scroll_offset = cursor_row - max_visible_rows + 1

            self.redraw(cursor, scroll_offset)
            keycode = get_keycode(self.screen)

            if keycode is None:
                continue

            if keycode == Screen.KEY_ESCAPE or keycode == 27:
                break

            if keycode in (ord("d"), ord("D")):
                self.showing_deck = True
                cursor = 0
                scroll_offset = 0
            elif keycode in (ord("c"), ord("C")):
                self.showing_deck = False
                cursor = 0
                scroll_offset = 0
            elif keycode == Screen.KEY_LEFT and cards:
                cursor = max(0, cursor - 1)
            elif keycode == Screen.KEY_RIGHT and cards:
                cursor = min(len(cards) - 1, cursor + 1)
            elif keycode == Screen.KEY_UP and cards:
                new_cursor = cursor - self.cardsperline
                if new_cursor >= 0:
                    cursor = new_cursor
            elif keycode == Screen.KEY_DOWN and cards:
                new_cursor = cursor + self.cardsperline
                if new_cursor < len(cards):
                    cursor = new_cursor
