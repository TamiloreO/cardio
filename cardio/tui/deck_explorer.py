from typing import List, Optional, Protocol
from asciimatics.screen import Screen
from cardio import Card, Deck
from .utils import get_keycode, dPos, show_text
from .constants import Color
from .card_picker import CardPicker
from .tuibase import TUIBaseMixin


class DeckExplorerView(Protocol):
    """Protocol for DeckExplorer views, enabling dependency injection for testing."""

    def show(self) -> None: ...
    def close(self) -> None: ...
    def message(self, msg: str) -> None: ...


class DeckExplorer(TUIBaseMixin):
    """A read-only view for exploring cards in a deck or collection."""

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
            # Use provided screen (for reusing existing screen from mapview)
            self.screen = screen
            self.debug = kwargs.get("debug", False)
            self._owns_screen = False
        else:
            # Create own screen via TUIBaseMixin
            super().__init__(*args, **kwargs)
            self._owns_screen = True

        self.deck = deck
        self.collection = collection
        self.title = title
        self.showing_deck = True
        self._card_picker: Optional[CardPicker] = None
        self._update_card_picker()

    def _update_card_picker(self) -> None:
        """Update the CardPicker with current deck's cards."""
        cards = self._get_current_cards()
        self._card_picker = CardPicker(self.screen, cards) if cards else None

    def _get_current_cards(self) -> List[Card]:
        return self.deck.cards if self.showing_deck else self.collection.cards

    def _get_tab_label(self) -> str:
        deck_label = f"[D] Main Deck ({self.deck.size()})"
        collection_label = f"[C] Collection ({self.collection.size()})"
        if self.showing_deck:
            return f"${{{Color.YELLOW.value}}}{deck_label}${{7}}  |  {collection_label}"
        else:
            return f"{deck_label}  |  ${{{Color.YELLOW.value}}}{collection_label}${{7}}"

    def _draw_header(self) -> None:
        """Draw the header with title and tab labels."""
        show_text(self.screen, dPos(2, 0), self.title, color=Color.CYAN)
        show_text(self.screen, dPos(2, 1), self._get_tab_label())
        show_text(
            self.screen,
            dPos(self.screen.width - 30, 0),
            "ESC to close  |  D/C switch tabs",
            color=Color.GRAY,
        )

    def _draw_empty_message(self) -> None:
        """Draw message when deck is empty."""
        label = "Main Deck" if self.showing_deck else "Collection"
        show_text(
            self.screen,
            dPos(2, 5),
            f"No cards in {label}",
            color=Color.GRAY,
        )

    def redraw(self, cursor: int = 0) -> None:
        """Redraw the entire view."""
        self.screen.clear_buffer(0, 0, 0)
        self._draw_header()

        cards = self._get_current_cards()
        if not cards:
            self._draw_empty_message()
        elif self._card_picker:
            # Use CardPicker's redraw but we need to handle the header offset
            # CardPicker.redraw clears the buffer, so we redraw header after
            self._card_picker.redraw(cards, cursor)
            self._draw_header()

        self.screen.refresh()

    def _switch_tab(self, to_deck: bool) -> None:
        """Switch between deck and collection tabs."""
        if self.showing_deck != to_deck:
            self.showing_deck = to_deck
            self._update_card_picker()

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
            elif cards and self._card_picker:
                if keycode == Screen.KEY_LEFT:
                    cursor = max(0, cursor - 1)
                elif keycode == Screen.KEY_RIGHT:
                    cursor = min(len(cards) - 1, cursor + 1)
                elif keycode == Screen.KEY_UP:
                    new_cursor = cursor - self._card_picker.cardsperline
                    if new_cursor >= 0:
                        cursor = new_cursor
                elif keycode == Screen.KEY_DOWN:
                    new_cursor = cursor + self._card_picker.cardsperline
                    if new_cursor < len(cards):
                        cursor = new_cursor

    def close(self) -> None:
        """Close the view if we own the screen."""
        if self._owns_screen:
            super().close()
