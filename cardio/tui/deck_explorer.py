from typing import List, Optional, Protocol
from asciimatics.screen import Screen
from cardio import Card, Deck
from .utils import get_keycode, dPos, show_text
from .constants import Color, BOX_WIDTH, BOX_HEIGHT, BOX_PADDING_LEFT, BOX_PADDING_TOP
from .card_primitives import VisualState, show_card
from .tuibase import TUIBaseMixin


class DeckExplorerView(Protocol):
    """Protocol for DeckExplorer views, enabling dependency injection for testing."""

    def show(self) -> None: ...
    def close(self) -> None: ...
    def message(self, msg: str) -> None: ...


class DeckExplorer(TUIBaseMixin):
    """A read-only view for exploring cards in a deck or collection.
    
    Supports vertical scrolling when cards exceed screen height.
    """

    HEADER_HEIGHT = 3

    def __init__(
        self,
        deck: Deck,
        collection: Deck,
        title: str = "Deck Explorer",
        screen: Optional[Screen] = None,
        *args,
        **kwargs,
    ) -> None:
        if screen is not None:
            self._external_screen = screen
        else:
            self._external_screen = None
        
        super().__init__(*args, **kwargs)
        
        if self._external_screen is not None:
            self.screen = self._external_screen
            self._owns_screen = False
        else:
            self._owns_screen = True

        self.deck = deck
        self.collection = collection
        self.title = title
        self.showing_deck = True
        self.scroll_offset = 0
        
        self.gross_width = BOX_WIDTH + BOX_PADDING_LEFT
        self.gross_height = BOX_HEIGHT + BOX_PADDING_TOP + 1
        self.cards_per_row = max(1, (self.screen.width - 4) // self.gross_width)
        self.visible_rows = max(1, (self.screen.height - self.HEADER_HEIGHT - 2) // self.gross_height)

    def _get_current_cards(self) -> List[Card]:
        return self.deck.cards if self.showing_deck else self.collection.cards

    def _get_total_rows(self) -> int:
        cards = self._get_current_cards()
        if not cards:
            return 0
        return (len(cards) + self.cards_per_row - 1) // self.cards_per_row

    def _get_tab_label(self) -> str:
        deck_label = f"[D] Main Deck ({self.deck.size()})"
        collection_label = f"[C] Collection ({self.collection.size()})"
        if self.showing_deck:
            return f"${{{Color.YELLOW.value}}}{deck_label}${{7}}  |  {collection_label}"
        else:
            return f"{deck_label}  |  ${{{Color.YELLOW.value}}}{collection_label}${{7}}"

    def _dpos_from_visible_index(self, visible_idx: int) -> dPos:
        """Get display position for a card at the given visible index (after scrolling)."""
        x = 2 + (visible_idx % self.cards_per_row) * self.gross_width
        y = self.HEADER_HEIGHT + (visible_idx // self.cards_per_row) * self.gross_height
        return dPos(x, y)

    def _switch_tab(self, to_deck: bool) -> None:
        """Switch between deck and collection tabs."""
        if self.showing_deck != to_deck:
            self.showing_deck = to_deck
            self.scroll_offset = 0

    def _adjust_scroll_for_cursor(self, cursor: int) -> None:
        """Adjust scroll offset to keep cursor visible."""
        cursor_row = cursor // self.cards_per_row
        if cursor_row < self.scroll_offset:
            self.scroll_offset = cursor_row
        elif cursor_row >= self.scroll_offset + self.visible_rows:
            self.scroll_offset = cursor_row - self.visible_rows + 1

    def redraw(self, cursor: int = 0) -> None:
        """Redraw the entire view in a single pass to avoid flicker."""
        self.screen.clear_buffer(0, 0, 0)
        
        # Draw header
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
            label = "Main Deck" if self.showing_deck else "Collection"
            show_text(
                self.screen,
                dPos(2, 5),
                f"No cards in {label}",
                color=Color.GRAY,
            )
        else:
            # Calculate visible range based on scroll
            start_idx = self.scroll_offset * self.cards_per_row
            max_visible = self.visible_rows * self.cards_per_row
            end_idx = min(start_idx + max_visible, len(cards))

            # Draw visible cards
            for i in range(start_idx, end_idx):
                visible_idx = i - start_idx
                pos = self._dpos_from_visible_index(visible_idx)
                
                if pos.y + BOX_HEIGHT > self.screen.height - 1:
                    break

                state = VisualState.CURSOR if i == cursor else VisualState.NORMAL
                show_card(self.screen, cards[i], pos, state)

            # Show scroll indicator if needed
            total_rows = self._get_total_rows()
            if total_rows > self.visible_rows:
                current_end_row = min(self.scroll_offset + self.visible_rows, total_rows)
                show_text(
                    self.screen,
                    dPos(2, self.screen.height - 1),
                    f"Rows {self.scroll_offset + 1}-{current_end_row} of {total_rows} (↑↓ to scroll)",
                    color=Color.GRAY,
                )

        self.screen.refresh()

    def show(self) -> None:
        """Show the deck explorer and allow navigation. Press ESC to close."""
        cursor = 0

        while True:
            cards = self._get_current_cards()

            # Adjust cursor if out of bounds
            if cards:
                cursor = min(cursor, len(cards) - 1)
            else:
                cursor = 0

            self._adjust_scroll_for_cursor(cursor)
            self.redraw(cursor)
            keycode = get_keycode(self.screen)

            if keycode is None:
                continue

            if keycode == Screen.KEY_ESCAPE or keycode == 27:
                break

            if keycode in (ord("d"), ord("D")):
                self._switch_tab(to_deck=True)
                cursor = 0
            elif keycode in (ord("c"), ord("C")):
                self._switch_tab(to_deck=False)
                cursor = 0
            elif cards:
                if keycode == Screen.KEY_LEFT:
                    cursor = max(0, cursor - 1)
                elif keycode == Screen.KEY_RIGHT:
                    cursor = min(len(cards) - 1, cursor + 1)
                elif keycode == Screen.KEY_UP:
                    new_cursor = cursor - self.cards_per_row
                    if new_cursor >= 0:
                        cursor = new_cursor
                elif keycode == Screen.KEY_DOWN:
                    new_cursor = cursor + self.cards_per_row
                    if new_cursor < len(cards):
                        cursor = new_cursor

    def close(self) -> None:
        """Close the view if we own the screen."""
        if self._owns_screen:
            super().close()
