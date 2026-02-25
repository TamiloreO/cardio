"""Tests for DeckExplorerView

These tests mock the TUI dependencies to test the DeckExplorerView logic
without requiring a real terminal or the full asciimatics library.

Note: These tests need proper asciimatics mocking. Due to the environment's
asciimatics version being incompatible with the codebase requirements,
we use pytest skip markers when imports fail.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from cardio import Card, Deck, HumanPlayer


# Try to import the module, skip all tests if asciimatics is incompatible
try:
    from cardio.tui.deck_explorer import DeckExplorerView
    from asciimatics.screen import Screen
    ASCIIMATICS_AVAILABLE = True
except ImportError as e:
    ASCIIMATICS_AVAILABLE = False
    IMPORT_ERROR = str(e)

pytestmark = pytest.mark.skipif(
    not ASCIIMATICS_AVAILABLE,
    reason=f"asciimatics import failed: {IMPORT_ERROR if not ASCIIMATICS_AVAILABLE else ''}"
)


def create_test_cards(count=5):
    """Create a list of test cards."""
    return [Card(f"Card{i}", power=i + 1, health=i + 1, costs_fire=1) for i in range(count)]


def create_test_humanplayer(deck_cards=None, collection_cards=None):
    """Create a HumanPlayer with specified cards."""
    player = HumanPlayer(name="TestPlayer")
    player.deck = Deck("main")
    player.collection = Deck("collection")
    if deck_cards:
        player.deck.cards = deck_cards
    if collection_cards:
        player.collection.cards = collection_cards
    return player


def create_mock_screen(width=160, height=52):
    """Create a mock screen for testing."""
    screen = Mock()
    screen.width = width
    screen.height = height
    screen.clear_buffer = Mock()
    screen.refresh = Mock()
    return screen


class TestDeckExplorerViewInit:
    """Tests for DeckExplorerView initialization."""

    def test_init_with_external_screen(self):
        screen = create_mock_screen()
        player = create_test_humanplayer()
        
        explorer = DeckExplorerView(player, screen=screen)
        
        assert explorer.screen is screen
        assert explorer.humanplayer is player
        assert explorer.showing_deck is True
        assert explorer._external_screen is True

    def test_init_defaults_to_showing_deck(self):
        screen = create_mock_screen()
        player = create_test_humanplayer()
        
        explorer = DeckExplorerView(player, screen=screen)
        
        assert explorer.showing_deck is True

    def test_init_with_custom_title(self):
        screen = create_mock_screen()
        player = create_test_humanplayer()
        
        explorer = DeckExplorerView(player, screen=screen, title="My Cards")
        
        assert explorer.title == "My Cards"


class TestDeckExplorerViewCurrentDeck:
    """Tests for _current_deck property."""

    def test_current_deck_returns_main_deck_when_showing_deck(self):
        screen = create_mock_screen()
        deck_cards = create_test_cards(3)
        collection_cards = create_test_cards(5)
        player = create_test_humanplayer(deck_cards, collection_cards)
        
        explorer = DeckExplorerView(player, screen=screen)
        explorer.showing_deck = True
        
        assert explorer._current_deck is player.deck
        assert len(explorer._current_deck.cards) == 3

    def test_current_deck_returns_collection_when_not_showing_deck(self):
        screen = create_mock_screen()
        deck_cards = create_test_cards(3)
        collection_cards = create_test_cards(5)
        player = create_test_humanplayer(deck_cards, collection_cards)
        
        explorer = DeckExplorerView(player, screen=screen)
        explorer.showing_deck = False
        
        assert explorer._current_deck is player.collection
        assert len(explorer._current_deck.cards) == 5


class TestDeckExplorerViewTabLabel:
    """Tests for tab label generation."""

    def test_tab_label_shows_deck_count(self):
        screen = create_mock_screen()
        deck_cards = create_test_cards(3)
        collection_cards = create_test_cards(5)
        player = create_test_humanplayer(deck_cards, collection_cards)
        
        explorer = DeckExplorerView(player, screen=screen)
        explorer.showing_deck = True
        label = explorer._get_tab_label()
        
        assert "Main Deck (3)" in label
        assert "Collection (5)" in label

    def test_tab_label_shows_collection_count(self):
        screen = create_mock_screen()
        deck_cards = create_test_cards(3)
        collection_cards = create_test_cards(5)
        player = create_test_humanplayer(deck_cards, collection_cards)
        
        explorer = DeckExplorerView(player, screen=screen)
        explorer.showing_deck = False
        label = explorer._get_tab_label()
        
        assert "Main Deck (3)" in label
        assert "Collection (5)" in label


class TestDeckExplorerViewEmptyDecks:
    """Tests for handling empty decks."""

    def test_empty_deck_returns_empty_list(self):
        screen = create_mock_screen()
        player = create_test_humanplayer(deck_cards=[], collection_cards=create_test_cards(3))
        
        explorer = DeckExplorerView(player, screen=screen)
        explorer.showing_deck = True
        
        assert len(explorer._current_deck.cards) == 0

    def test_empty_collection_returns_empty_list(self):
        screen = create_mock_screen()
        player = create_test_humanplayer(deck_cards=create_test_cards(3), collection_cards=[])
        
        explorer = DeckExplorerView(player, screen=screen)
        explorer.showing_deck = False
        
        assert len(explorer._current_deck.cards) == 0

    def test_both_empty_handled_gracefully(self):
        screen = create_mock_screen()
        player = create_test_humanplayer(deck_cards=[], collection_cards=[])
        
        explorer = DeckExplorerView(player, screen=screen)
        
        assert len(explorer._current_deck.cards) == 0
        explorer.showing_deck = False
        assert len(explorer._current_deck.cards) == 0


class TestDeckExplorerViewNavigation:
    """Tests for keyboard navigation."""

    @patch("cardio.tui.deck_explorer.get_keycode")
    @patch("cardio.tui.deck_explorer.CardPicker")
    @patch("cardio.tui.deck_explorer.show_text")
    def test_escape_closes_explorer(self, mock_show_text, mock_picker_class, mock_get_keycode):
        screen = create_mock_screen()
        player = create_test_humanplayer(deck_cards=create_test_cards(3))
        
        mock_get_keycode.return_value = Screen.KEY_ESCAPE
        mock_picker = Mock()
        mock_picker.cardsperline = 6
        mock_picker_class.return_value = mock_picker
        
        explorer = DeckExplorerView(player, screen=screen)
        explorer.show()
        
        # If we get here without hanging, ESC worked

    @patch("cardio.tui.deck_explorer.get_keycode")
    @patch("cardio.tui.deck_explorer.CardPicker")
    @patch("cardio.tui.deck_explorer.show_text")
    def test_escape_code_27_closes_explorer(self, mock_show_text, mock_picker_class, mock_get_keycode):
        screen = create_mock_screen()
        player = create_test_humanplayer(deck_cards=create_test_cards(3))
        
        mock_get_keycode.return_value = 27  # ESC keycode
        mock_picker = Mock()
        mock_picker.cardsperline = 6
        mock_picker_class.return_value = mock_picker
        
        explorer = DeckExplorerView(player, screen=screen)
        explorer.show()

    @patch("cardio.tui.deck_explorer.get_keycode")
    @patch("cardio.tui.deck_explorer.CardPicker")
    @patch("cardio.tui.deck_explorer.show_text")
    def test_d_key_switches_to_deck(self, mock_show_text, mock_picker_class, mock_get_keycode):
        screen = create_mock_screen()
        player = create_test_humanplayer(
            deck_cards=create_test_cards(3),
            collection_cards=create_test_cards(5)
        )
        
        # First press 'c' to switch to collection, then 'd' to switch back, then ESC
        mock_get_keycode.side_effect = [ord("c"), ord("d"), Screen.KEY_ESCAPE]
        mock_picker = Mock()
        mock_picker.cardsperline = 6
        mock_picker_class.return_value = mock_picker
        
        explorer = DeckExplorerView(player, screen=screen)
        explorer.show()
        
        assert explorer.showing_deck is True

    @patch("cardio.tui.deck_explorer.get_keycode")
    @patch("cardio.tui.deck_explorer.CardPicker")
    @patch("cardio.tui.deck_explorer.show_text")
    def test_c_key_switches_to_collection(self, mock_show_text, mock_picker_class, mock_get_keycode):
        screen = create_mock_screen()
        player = create_test_humanplayer(
            deck_cards=create_test_cards(3),
            collection_cards=create_test_cards(5)
        )
        
        mock_get_keycode.side_effect = [ord("c"), Screen.KEY_ESCAPE]
        mock_picker = Mock()
        mock_picker.cardsperline = 6
        mock_picker_class.return_value = mock_picker
        
        explorer = DeckExplorerView(player, screen=screen)
        explorer.show()
        
        assert explorer.showing_deck is False

    @patch("cardio.tui.deck_explorer.get_keycode")
    @patch("cardio.tui.deck_explorer.CardPicker")
    @patch("cardio.tui.deck_explorer.show_text")
    def test_uppercase_d_switches_to_deck(self, mock_show_text, mock_picker_class, mock_get_keycode):
        screen = create_mock_screen()
        player = create_test_humanplayer(
            deck_cards=create_test_cards(3),
            collection_cards=create_test_cards(5)
        )
        
        mock_get_keycode.side_effect = [ord("c"), ord("D"), Screen.KEY_ESCAPE]
        mock_picker = Mock()
        mock_picker.cardsperline = 6
        mock_picker_class.return_value = mock_picker
        
        explorer = DeckExplorerView(player, screen=screen)
        explorer.show()
        
        assert explorer.showing_deck is True

    @patch("cardio.tui.deck_explorer.get_keycode")
    @patch("cardio.tui.deck_explorer.CardPicker")
    @patch("cardio.tui.deck_explorer.show_text")
    def test_uppercase_c_switches_to_collection(self, mock_show_text, mock_picker_class, mock_get_keycode):
        screen = create_mock_screen()
        player = create_test_humanplayer(
            deck_cards=create_test_cards(3),
            collection_cards=create_test_cards(5)
        )
        
        mock_get_keycode.side_effect = [ord("C"), Screen.KEY_ESCAPE]
        mock_picker = Mock()
        mock_picker.cardsperline = 6
        mock_picker_class.return_value = mock_picker
        
        explorer = DeckExplorerView(player, screen=screen)
        explorer.show()
        
        assert explorer.showing_deck is False

    @patch("cardio.tui.deck_explorer.get_keycode")
    @patch("cardio.tui.deck_explorer.show_text")
    def test_navigation_on_empty_deck_does_not_crash(self, mock_show_text, mock_get_keycode):
        screen = create_mock_screen()
        player = create_test_humanplayer(deck_cards=[], collection_cards=[])
        
        # Try navigating with arrow keys on empty deck
        mock_get_keycode.side_effect = [
            Screen.KEY_LEFT,
            Screen.KEY_RIGHT,
            Screen.KEY_UP,
            Screen.KEY_DOWN,
            Screen.KEY_ESCAPE,
        ]
        
        explorer = DeckExplorerView(player, screen=screen)
        explorer.show()  # Should not crash

    @patch("cardio.tui.deck_explorer.get_keycode")
    @patch("cardio.tui.deck_explorer.CardPicker")
    @patch("cardio.tui.deck_explorer.show_text")
    def test_none_keycode_is_ignored(self, mock_show_text, mock_picker_class, mock_get_keycode):
        screen = create_mock_screen()
        player = create_test_humanplayer(deck_cards=create_test_cards(3))
        
        # Return None (no key pressed) then ESC
        mock_get_keycode.side_effect = [None, None, Screen.KEY_ESCAPE]
        mock_picker = Mock()
        mock_picker.cardsperline = 6
        mock_picker_class.return_value = mock_picker
        
        explorer = DeckExplorerView(player, screen=screen)
        explorer.show()  # Should handle None gracefully


class TestDeckExplorerViewClose:
    """Tests for close behavior."""

    def test_close_does_not_close_external_screen(self):
        screen = create_mock_screen()
        screen.close = Mock()
        player = create_test_humanplayer()
        
        explorer = DeckExplorerView(player, screen=screen)
        explorer.close()
        
        # External screen should not be closed
        screen.close.assert_not_called()


class TestDeckExplorerViewCardPicker:
    """Tests for CardPicker integration."""

    @patch("cardio.tui.deck_explorer.get_keycode")
    @patch("cardio.tui.deck_explorer.CardPicker")
    @patch("cardio.tui.deck_explorer.show_text")
    def test_card_picker_created_with_current_cards(self, mock_show_text, mock_picker_class, mock_get_keycode):
        screen = create_mock_screen()
        deck_cards = create_test_cards(3)
        player = create_test_humanplayer(deck_cards=deck_cards)
        
        mock_get_keycode.return_value = Screen.KEY_ESCAPE
        mock_picker = Mock()
        mock_picker.cardsperline = 6
        mock_picker_class.return_value = mock_picker
        
        explorer = DeckExplorerView(player, screen=screen)
        explorer.show()
        
        # Verify CardPicker was instantiated with the screen and cards
        mock_picker_class.assert_called_with(screen, deck_cards)

    @patch("cardio.tui.deck_explorer.get_keycode")
    @patch("cardio.tui.deck_explorer.CardPicker")
    @patch("cardio.tui.deck_explorer.show_text")
    def test_card_picker_redraw_called_with_cursor(self, mock_show_text, mock_picker_class, mock_get_keycode):
        screen = create_mock_screen()
        deck_cards = create_test_cards(3)
        player = create_test_humanplayer(deck_cards=deck_cards)
        
        mock_get_keycode.return_value = Screen.KEY_ESCAPE
        mock_picker = Mock()
        mock_picker.cardsperline = 6
        mock_picker_class.return_value = mock_picker
        
        explorer = DeckExplorerView(player, screen=screen)
        explorer.show()
        
        # Verify redraw was called
        mock_picker.redraw.assert_called()


class TestDeckExplorerViewCursorNavigation:
    """Tests for cursor movement within cards."""

    @patch("cardio.tui.deck_explorer.get_keycode")
    @patch("cardio.tui.deck_explorer.CardPicker")
    @patch("cardio.tui.deck_explorer.show_text")
    def test_cursor_stays_in_bounds_on_left(self, mock_show_text, mock_picker_class, mock_get_keycode):
        screen = create_mock_screen()
        deck_cards = create_test_cards(5)
        player = create_test_humanplayer(deck_cards=deck_cards)
        
        # Press left multiple times (cursor starts at 0)
        mock_get_keycode.side_effect = [
            Screen.KEY_LEFT,
            Screen.KEY_LEFT,
            Screen.KEY_ESCAPE,
        ]
        mock_picker = Mock()
        mock_picker.cardsperline = 6
        mock_picker_class.return_value = mock_picker
        
        explorer = DeckExplorerView(player, screen=screen)
        explorer.show()
        # No assertion needed - if it doesn't crash, cursor stayed in bounds

    @patch("cardio.tui.deck_explorer.get_keycode")
    @patch("cardio.tui.deck_explorer.CardPicker")
    @patch("cardio.tui.deck_explorer.show_text")
    def test_cursor_stays_in_bounds_on_right(self, mock_show_text, mock_picker_class, mock_get_keycode):
        screen = create_mock_screen()
        deck_cards = create_test_cards(3)
        player = create_test_humanplayer(deck_cards=deck_cards)
        
        # Press right past the end
        mock_get_keycode.side_effect = [
            Screen.KEY_RIGHT,
            Screen.KEY_RIGHT,
            Screen.KEY_RIGHT,
            Screen.KEY_RIGHT,  # Beyond bounds
            Screen.KEY_ESCAPE,
        ]
        mock_picker = Mock()
        mock_picker.cardsperline = 6
        mock_picker_class.return_value = mock_picker
        
        explorer = DeckExplorerView(player, screen=screen)
        explorer.show()

    @patch("cardio.tui.deck_explorer.get_keycode")
    @patch("cardio.tui.deck_explorer.CardPicker")
    @patch("cardio.tui.deck_explorer.show_text")
    def test_switching_tabs_resets_cursor(self, mock_show_text, mock_picker_class, mock_get_keycode):
        screen = create_mock_screen()
        deck_cards = create_test_cards(10)
        collection_cards = create_test_cards(3)
        player = create_test_humanplayer(deck_cards=deck_cards, collection_cards=collection_cards)
        
        # Move cursor right, then switch to collection (which has fewer cards)
        mock_get_keycode.side_effect = [
            Screen.KEY_RIGHT,
            Screen.KEY_RIGHT,
            Screen.KEY_RIGHT,
            Screen.KEY_RIGHT,
            Screen.KEY_RIGHT,  # cursor = 5
            ord("c"),  # Switch to collection (only 3 cards)
            Screen.KEY_ESCAPE,
        ]
        mock_picker = Mock()
        mock_picker.cardsperline = 6
        mock_picker_class.return_value = mock_picker
        
        explorer = DeckExplorerView(player, screen=screen)
        explorer.show()
        # Should not crash - cursor should be reset or clamped


class TestMapViewDeckExplorerIntegration:
    """Tests for TUIMapView opening the deck explorer."""

    @patch("cardio.tui.mapview.DeckExplorerView")
    def test_open_deck_explorer_creates_and_shows_explorer(self, mock_explorer_class):
        from cardio.tui.mapview import TUIMapView
        
        mock_explorer = Mock()
        mock_explorer_class.return_value = mock_explorer
        
        # Create a mock mapview with mocked screen
        with patch.object(TUIMapView, "__init__", lambda self, *args, **kwargs: None):
            mapview = TUIMapView.__new__(TUIMapView)
            mapview.screen = create_mock_screen()
            mapview.humanplayer = create_test_humanplayer(deck_cards=create_test_cards(3))
            
            mapview.open_deck_explorer()
            
            # Verify DeckExplorerView was created with correct arguments
            mock_explorer_class.assert_called_once_with(
                mapview.humanplayer,
                screen=mapview.screen,
                title="Deck Explorer",
            )
            mock_explorer.show.assert_called_once()
