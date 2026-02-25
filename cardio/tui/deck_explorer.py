from typing import Optional
from asciimatics.screen import Screen
from cardio import Deck
from cardio.human_player import HumanPlayer
from .card_picker import CardPicker
from .tuibase import TUIBaseMixin
from .utils import get_keycode, dPos, show_text
from .constants import Color


class DeckExplorerView(TUIBaseMixin):
    """A read-only view for exploring cards in the player's deck and collection.
    
    Can be used standalone (creates its own screen) or with an existing screen
    from a parent view like TUIMapView.
    """

    def __init__(
        self,
        humanplayer: HumanPlayer,
        screen: Optional[Screen] = None,
        title: str = "Deck Explorer",
        *args,
        **kwargs,
    ) -> None:
        self._external_screen = screen is not None
        if self._external_screen:
            # Use provided screen, skip TUIBaseMixin screen creation
            self.screen = screen
            self.debug = kwargs.get("debug", False)
        else:
            # Create our own screen via TUIBaseMixin
            super().__init__(*args, **kwargs)

        self.humanplayer = humanplayer
        self.title = title
        self.showing_deck = True  # True = main deck, False = collection

    def close(self) -> None:
        """Only close screen if we created it ourselves."""
        if not self._external_screen:
            super().close()

    @property
    def _current_deck(self) -> Deck:
        return self.humanplayer.deck if self.showing_deck else self.humanplayer.collection

    def _get_tab_label(self) -> str:
        deck_label = f"[D] Main Deck ({self.humanplayer.deck.size()})"
        collection_label = f"[C] Collection ({self.humanplayer.collection.size()})"
        if self.showing_deck:
            return f"${{{Color.YELLOW.value}}}{deck_label}${{7}}  |  {collection_label}"
        else:
            return f"{deck_label}  |  ${{{Color.YELLOW.value}}}{collection_label}${{7}}"

    def _draw_header(self) -> None:
        show_text(self.screen, dPos(2, 0), self.title, color=Color.CYAN)
        show_text(self.screen, dPos(2, 1), self._get_tab_label())
        show_text(
            self.screen,
            dPos(self.screen.width - 30, 0),
            "ESC to close  |  D/C switch tabs",
            color=Color.GRAY,
        )

    def _draw_empty_message(self) -> None:
        deck_name = "deck" if self.showing_deck else "collection"
        show_text(
            self.screen,
            dPos(2, 5),
            f"No cards in this {deck_name}",
            color=Color.GRAY,
        )

    def _create_card_picker(self) -> Optional[CardPicker]:
        cards = self._current_deck.cards
        if not cards:
            return None
        return CardPicker(self.screen, cards)

    def show(self) -> None:
        """Show the deck explorer. Navigate with arrow keys, ESC to close."""
        cursor = 0

        while True:
            self.screen.clear_buffer(0, 0, 0)
            self._draw_header()

            cards = self._current_deck.cards
            if not cards:
                self._draw_empty_message()
                self.screen.refresh()
            else:
                cursor = min(cursor, len(cards) - 1)
                picker = CardPicker(self.screen, cards)
                picker.redraw(activecards=cards, cursor=cursor)
                self._draw_header()  # Redraw header on top of picker
                self.screen.refresh()

            keycode = get_keycode(self.screen)
            if keycode is None:
                continue

            if keycode == Screen.KEY_ESCAPE or keycode == 27:
                break

            if keycode in (ord("d"), ord("D")):
                self.showing_deck = True
                cursor = 0
            elif keycode in (ord("c"), ord("C")):
                self.showing_deck = False
                cursor = 0
            elif cards:
                picker = CardPicker(self.screen, cards)
                if keycode == Screen.KEY_LEFT:
                    cursor = max(0, cursor - 1)
                elif keycode == Screen.KEY_RIGHT:
                    cursor = min(len(cards) - 1, cursor + 1)
                elif keycode == Screen.KEY_UP:
                    new_cursor = cursor - picker.cardsperline
                    if new_cursor >= 0:
                        cursor = new_cursor
                elif keycode == Screen.KEY_DOWN:
                    new_cursor = cursor + picker.cardsperline
                    if new_cursor < len(cards):
                        cursor = new_cursor
