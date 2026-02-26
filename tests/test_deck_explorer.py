"""Tests for DeckExplorer functionality.

These tests verify the core logic of DeckExplorer without requiring
a working terminal/screen. The tests mock the screen and UI components.

Note: These tests require asciimatics >= 1.14.0 for SINGLE_LINE/DOUBLE_LINE constants.
"""

import pytest
from unittest.mock import Mock, patch, call

# Skip all tests in this module if asciimatics constants are not available
try:
    from asciimatics.constants import SINGLE_LINE, DOUBLE_LINE
    ASCIIMATICS_AVAILABLE = True
except ImportError:
    ASCIIMATICS_AVAILABLE = False

pytestmark = pytest.mark.skipif(
    not ASCIIMATICS_AVAILABLE,
    reason="asciimatics >= 1.14.0 required for these tests"
)

from cardio import Card, Deck


def create_test_cards(count: int) -> list:
    """Create a list of test cards."""
    return [Card(f"Card{i}", power=i + 1, health=i + 1, costs_fire=1) for i in range(count)]


@pytest.fixture
def mock_screen():
    """Create a mock screen for testing."""
    screen = Mock()
    screen.width = 160
    screen.height = 52
    screen.clear_buffer = Mock()
    screen.refresh = Mock()
    screen.close = Mock()
    return screen


class TestDeckExplorerInit:
    """Tests for DeckExplorer initialization."""

    def test_init_with_provided_screen(self, mock_screen):
        from cardio.tui.deck_explorer import DeckExplorer

        deck = Deck("main", create_test_cards(3))
        collection = Deck("collection", create_test_cards(5))

        explorer = DeckExplorer(
            deck=deck,
            collection=collection,
            screen=mock_screen,
        )

        assert explorer.deck is deck
        assert explorer.collection is collection
        assert explorer.screen is mock_screen
        assert explorer.showing_deck is True
        assert explorer._provided_screen is mock_screen

    def test_init_with_empty_decks(self, mock_screen):
        from cardio.tui.deck_explorer import DeckExplorer

        deck = Deck("main")
        collection = Deck("collection")

        explorer = DeckExplorer(
            deck=deck,
            collection=collection,
            screen=mock_screen,
        )

        assert explorer.deck.size() == 0
        assert explorer.collection.size() == 0

    def test_init_with_custom_title(self, mock_screen):
        from cardio.tui.deck_explorer import DeckExplorer

        deck = Deck("main", create_test_cards(1))
        collection = Deck("collection")

        explorer = DeckExplorer(
            deck=deck,
            collection=collection,
            title="Custom Title",
            screen=mock_screen,
        )

        assert explorer.title == "Custom Title"

    def test_init_calculates_layout(self, mock_screen):
        from cardio.tui.deck_explorer import DeckExplorer

        deck = Deck("main", create_test_cards(3))
        collection = Deck("collection")

        explorer = DeckExplorer(deck=deck, collection=collection, screen=mock_screen)

        assert explorer.cards_per_row > 0
        assert explorer.visible_rows > 0
        assert explorer.scroll_offset == 0


class TestDeckExplorerCardAccess:
    """Tests for accessing cards in the explorer."""

    def test_get_current_cards_returns_deck_by_default(self, mock_screen):
        from cardio.tui.deck_explorer import DeckExplorer

        deck_cards = create_test_cards(3)
        collection_cards = create_test_cards(5)
        deck = Deck("main", deck_cards)
        collection = Deck("collection", collection_cards)

        explorer = DeckExplorer(deck=deck, collection=collection, screen=mock_screen)

        assert explorer._get_current_cards() == deck_cards

    def test_get_current_cards_returns_collection_when_switched(self, mock_screen):
        from cardio.tui.deck_explorer import DeckExplorer

        deck_cards = create_test_cards(3)
        collection_cards = create_test_cards(5)
        deck = Deck("main", deck_cards)
        collection = Deck("collection", collection_cards)

        explorer = DeckExplorer(deck=deck, collection=collection, screen=mock_screen)
        explorer._switch_tab(to_deck=False)

        assert explorer._get_current_cards() == collection_cards


class TestDeckExplorerTabSwitching:
    """Tests for tab switching functionality."""

    def test_switch_to_collection(self, mock_screen):
        from cardio.tui.deck_explorer import DeckExplorer

        deck = Deck("main", create_test_cards(3))
        collection = Deck("collection", create_test_cards(5))

        explorer = DeckExplorer(deck=deck, collection=collection, screen=mock_screen)
        assert explorer.showing_deck is True

        explorer._switch_tab(to_deck=False)

        assert explorer.showing_deck is False

    def test_switch_to_deck(self, mock_screen):
        from cardio.tui.deck_explorer import DeckExplorer

        deck = Deck("main", create_test_cards(3))
        collection = Deck("collection", create_test_cards(5))

        explorer = DeckExplorer(deck=deck, collection=collection, screen=mock_screen)
        explorer._switch_tab(to_deck=False)
        assert explorer.showing_deck is False

        explorer._switch_tab(to_deck=True)

        assert explorer.showing_deck is True

    def test_switch_resets_scroll_offset(self, mock_screen):
        from cardio.tui.deck_explorer import DeckExplorer

        deck = Deck("main", create_test_cards(3))
        collection = Deck("collection", create_test_cards(5))

        explorer = DeckExplorer(deck=deck, collection=collection, screen=mock_screen)
        explorer.scroll_offset = 5  # Simulate scrolled state

        explorer._switch_tab(to_deck=False)

        assert explorer.scroll_offset == 0


class TestDeckExplorerNavigation:
    """Tests for keyboard navigation."""

    def test_escape_key_closes_explorer(self, mock_screen):
        from cardio.tui.deck_explorer import DeckExplorer

        deck = Deck("main", create_test_cards(3))
        collection = Deck("collection")

        explorer = DeckExplorer(deck=deck, collection=collection, screen=mock_screen)

        with patch('cardio.tui.deck_explorer.get_keycode') as mock_keycode:
            mock_keycode.return_value = 27  # ESC key
            explorer.show()

        # If we reach here without hanging, ESC was handled correctly
        assert True

    def test_d_key_switches_to_deck(self, mock_screen):
        from cardio.tui.deck_explorer import DeckExplorer

        deck = Deck("main", create_test_cards(3))
        collection = Deck("collection", create_test_cards(5))

        explorer = DeckExplorer(deck=deck, collection=collection, screen=mock_screen)
        explorer._switch_tab(to_deck=False)

        with patch('cardio.tui.deck_explorer.get_keycode') as mock_keycode:
            mock_keycode.side_effect = [ord('d'), 27]  # d then ESC
            explorer.show()

        assert explorer.showing_deck is True

    def test_c_key_switches_to_collection(self, mock_screen):
        from cardio.tui.deck_explorer import DeckExplorer

        deck = Deck("main", create_test_cards(3))
        collection = Deck("collection", create_test_cards(5))

        explorer = DeckExplorer(deck=deck, collection=collection, screen=mock_screen)

        with patch('cardio.tui.deck_explorer.get_keycode') as mock_keycode:
            mock_keycode.side_effect = [ord('c'), 27]  # c then ESC
            explorer.show()

        assert explorer.showing_deck is False

    def test_right_arrow_increases_cursor(self, mock_screen):
        from cardio.tui.deck_explorer import DeckExplorer
        from asciimatics.screen import Screen

        deck = Deck("main", create_test_cards(10))
        collection = Deck("collection")

        explorer = DeckExplorer(deck=deck, collection=collection, screen=mock_screen)
        cursor_values = []

        def capture_cursor(cursor=0):
            cursor_values.append(cursor)
        explorer.redraw = capture_cursor

        with patch('cardio.tui.deck_explorer.get_keycode') as mock_keycode:
            mock_keycode.side_effect = [Screen.KEY_RIGHT, Screen.KEY_RIGHT, 27]
            explorer.show()

        # Cursor should move: 0 -> 1 -> 2
        assert cursor_values == [0, 1, 2]

    def test_left_arrow_decreases_cursor(self, mock_screen):
        from cardio.tui.deck_explorer import DeckExplorer
        from asciimatics.screen import Screen

        deck = Deck("main", create_test_cards(10))
        collection = Deck("collection")

        explorer = DeckExplorer(deck=deck, collection=collection, screen=mock_screen)
        cursor_values = []

        def capture_cursor(cursor=0):
            cursor_values.append(cursor)
        explorer.redraw = capture_cursor

        with patch('cardio.tui.deck_explorer.get_keycode') as mock_keycode:
            # Move right twice, then left once
            mock_keycode.side_effect = [
                Screen.KEY_RIGHT, Screen.KEY_RIGHT, Screen.KEY_LEFT, 27
            ]
            explorer.show()

        assert cursor_values == [0, 1, 2, 1]

    def test_cursor_does_not_go_below_zero(self, mock_screen):
        from cardio.tui.deck_explorer import DeckExplorer
        from asciimatics.screen import Screen

        deck = Deck("main", create_test_cards(3))
        collection = Deck("collection")

        explorer = DeckExplorer(deck=deck, collection=collection, screen=mock_screen)
        cursor_values = []

        def capture_cursor(cursor=0):
            cursor_values.append(cursor)
        explorer.redraw = capture_cursor

        with patch('cardio.tui.deck_explorer.get_keycode') as mock_keycode:
            mock_keycode.side_effect = [Screen.KEY_LEFT, Screen.KEY_LEFT, 27]
            explorer.show()

        # Cursor should stay at 0
        assert cursor_values == [0, 0, 0]

    def test_cursor_does_not_exceed_card_count(self, mock_screen):
        from cardio.tui.deck_explorer import DeckExplorer
        from asciimatics.screen import Screen

        deck = Deck("main", create_test_cards(3))  # Only 3 cards
        collection = Deck("collection")

        explorer = DeckExplorer(deck=deck, collection=collection, screen=mock_screen)
        cursor_values = []

        def capture_cursor(cursor=0):
            cursor_values.append(cursor)
        explorer.redraw = capture_cursor

        with patch('cardio.tui.deck_explorer.get_keycode') as mock_keycode:
            # Try to move right 5 times (but only 3 cards)
            mock_keycode.side_effect = [
                Screen.KEY_RIGHT, Screen.KEY_RIGHT, Screen.KEY_RIGHT,
                Screen.KEY_RIGHT, Screen.KEY_RIGHT, 27
            ]
            explorer.show()

        # Cursor should max out at 2 (index of last card)
        assert cursor_values[-1] == 2


class TestDeckExplorerScrolling:
    """Tests for vertical scrolling functionality."""

    def test_scroll_offset_adjusts_when_cursor_moves_down(self, mock_screen):
        from cardio.tui.deck_explorer import DeckExplorer

        # Create enough cards to require scrolling (more than visible_rows * cards_per_row)
        deck = Deck("main", create_test_cards(50))
        collection = Deck("collection")

        explorer = DeckExplorer(deck=deck, collection=collection, screen=mock_screen)
        
        # Set cursor to a position that would be off-screen
        cursor = explorer.visible_rows * explorer.cards_per_row + 1
        explorer._adjust_scroll_for_cursor(cursor)

        assert explorer.scroll_offset > 0

    def test_scroll_offset_adjusts_when_cursor_moves_up(self, mock_screen):
        from cardio.tui.deck_explorer import DeckExplorer

        deck = Deck("main", create_test_cards(50))
        collection = Deck("collection")

        explorer = DeckExplorer(deck=deck, collection=collection, screen=mock_screen)
        explorer.scroll_offset = 3  # Start scrolled down
        
        # Move cursor to first row
        cursor = 0
        explorer._adjust_scroll_for_cursor(cursor)

        assert explorer.scroll_offset == 0

    def test_down_arrow_scrolls_when_needed(self, mock_screen):
        from cardio.tui.deck_explorer import DeckExplorer
        from asciimatics.screen import Screen

        # Create many cards to require scrolling
        deck = Deck("main", create_test_cards(100))
        collection = Deck("collection")

        explorer = DeckExplorer(deck=deck, collection=collection, screen=mock_screen)
        scroll_values = []

        original_redraw = explorer.redraw
        def capture_scroll(cursor=0):
            scroll_values.append(explorer.scroll_offset)
        explorer.redraw = capture_scroll

        with patch('cardio.tui.deck_explorer.get_keycode') as mock_keycode:
            # Press down many times to trigger scrolling
            num_downs = explorer.visible_rows + 2
            mock_keycode.side_effect = [Screen.KEY_DOWN] * num_downs + [27]
            explorer.show()

        # Scroll should have increased at some point
        assert max(scroll_values) > 0

    def test_get_total_rows_calculation(self, mock_screen):
        from cardio.tui.deck_explorer import DeckExplorer

        deck = Deck("main", create_test_cards(25))
        collection = Deck("collection")

        explorer = DeckExplorer(deck=deck, collection=collection, screen=mock_screen)
        
        expected_rows = (25 + explorer.cards_per_row - 1) // explorer.cards_per_row
        assert explorer._get_total_rows() == expected_rows

    def test_get_total_rows_empty_deck(self, mock_screen):
        from cardio.tui.deck_explorer import DeckExplorer

        deck = Deck("main")
        collection = Deck("collection")

        explorer = DeckExplorer(deck=deck, collection=collection, screen=mock_screen)
        
        assert explorer._get_total_rows() == 0

    def test_cursor_to_row_conversion(self, mock_screen):
        from cardio.tui.deck_explorer import DeckExplorer

        deck = Deck("main", create_test_cards(20))
        collection = Deck("collection")

        explorer = DeckExplorer(deck=deck, collection=collection, screen=mock_screen)
        
        # First row
        assert explorer._cursor_to_row(0) == 0
        assert explorer._cursor_to_row(explorer.cards_per_row - 1) == 0
        
        # Second row
        assert explorer._cursor_to_row(explorer.cards_per_row) == 1


class TestDeckExplorerEmptyDecks:
    """Tests for handling empty decks."""

    def test_empty_deck_handled_gracefully(self, mock_screen):
        from cardio.tui.deck_explorer import DeckExplorer

        deck = Deck("main")  # Empty
        collection = Deck("collection")  # Empty

        explorer = DeckExplorer(deck=deck, collection=collection, screen=mock_screen)

        with patch('cardio.tui.deck_explorer.get_keycode') as mock_keycode:
            mock_keycode.return_value = 27  # ESC
            explorer.show()

        # Should complete without errors
        assert True

    def test_navigation_noop_for_empty_deck(self, mock_screen):
        from cardio.tui.deck_explorer import DeckExplorer
        from asciimatics.screen import Screen

        deck = Deck("main")
        collection = Deck("collection")

        explorer = DeckExplorer(deck=deck, collection=collection, screen=mock_screen)
        cursor_values = []

        def capture_cursor(cursor=0):
            cursor_values.append(cursor)
        explorer.redraw = capture_cursor

        with patch('cardio.tui.deck_explorer.get_keycode') as mock_keycode:
            mock_keycode.side_effect = [
                Screen.KEY_RIGHT, Screen.KEY_LEFT, Screen.KEY_UP, Screen.KEY_DOWN, 27
            ]
            explorer.show()

        # All cursor values should be 0 since deck is empty
        assert all(c == 0 for c in cursor_values)


class TestDeckExplorerTabLabels:
    """Tests for tab label generation."""

    def test_tab_label_shows_deck_count(self, mock_screen):
        from cardio.tui.deck_explorer import DeckExplorer

        deck = Deck("main", create_test_cards(3))
        collection = Deck("collection", create_test_cards(7))

        explorer = DeckExplorer(deck=deck, collection=collection, screen=mock_screen)

        label = explorer._get_tab_label()

        assert "(3)" in label
        assert "(7)" in label

    def test_deck_label_content(self, mock_screen):
        from cardio.tui.deck_explorer import DeckExplorer

        deck = Deck("main", create_test_cards(3))
        collection = Deck("collection", create_test_cards(5))

        explorer = DeckExplorer(deck=deck, collection=collection, screen=mock_screen)

        label = explorer._get_tab_label()

        assert "[D] Main Deck" in label
        assert "[C] Collection" in label


class TestDeckExplorerClose:
    """Tests for closing the explorer."""

    def test_close_does_not_close_borrowed_screen(self, mock_screen):
        from cardio.tui.deck_explorer import DeckExplorer

        deck = Deck("main")
        collection = Deck("collection")

        explorer = DeckExplorer(deck=deck, collection=collection, screen=mock_screen)
        assert explorer._provided_screen is mock_screen

        explorer.close()

        # screen.close() should NOT have been called since we borrowed the screen
        mock_screen.close.assert_not_called()


class TestMapViewDeckExplorerIntegration:
    """Tests for opening deck explorer from map view."""

    def test_d_key_opens_deck_explorer_from_mapview(self, mock_screen):
        """Test that pressing D key in map view opens the deck explorer."""
        from asciimatics.screen import Screen
        
        with patch('cardio.tui.mapview.DeckExplorer') as MockDeckExplorer:
            mock_explorer_instance = Mock()
            MockDeckExplorer.return_value = mock_explorer_instance

            from cardio.tui.mapview import TUIMapView
            from cardio import HumanPlayer, Deck
            from cardio.run import Run

            human = HumanPlayer(name="Test")
            human.deck = Deck("main", create_test_cards(3))
            human.collection = Deck("collection", create_test_cards(5))

            with patch.object(TUIMapView, '__init__', lambda self, *args, **kwargs: None):
                mapview = TUIMapView.__new__(TUIMapView)
                mapview.screen = mock_screen
                mapview.humanplayer = human
                mapview.debug = False
                mapview.run = Mock()
                mapview.run.get_accessible_locations.return_value = [Mock()]
                mapview.run.current_index = 0

                with patch('cardio.tui.mapview.get_keycode') as mock_keycode:
                    with patch.object(mapview, 'redraw'):
                        # Simulate: D key press, then Enter to select location
                        mock_keycode.side_effect = [ord('d'), 13]
                        mapview.get_next_location()

                # Verify DeckExplorer was created and shown
                MockDeckExplorer.assert_called_once()
                call_kwargs = MockDeckExplorer.call_args[1]
                assert call_kwargs['deck'] is human.deck
                assert call_kwargs['collection'] is human.collection
                assert call_kwargs['screen'] is mock_screen
                mock_explorer_instance.show.assert_called_once()

    def test_uppercase_d_key_also_opens_explorer(self, mock_screen):
        """Test that uppercase D also opens the deck explorer."""
        from asciimatics.screen import Screen
        
        with patch('cardio.tui.mapview.DeckExplorer') as MockDeckExplorer:
            mock_explorer_instance = Mock()
            MockDeckExplorer.return_value = mock_explorer_instance

            from cardio.tui.mapview import TUIMapView
            from cardio import HumanPlayer, Deck

            human = HumanPlayer(name="Test")
            human.deck = Deck("main", create_test_cards(3))
            human.collection = Deck("collection", create_test_cards(5))

            with patch.object(TUIMapView, '__init__', lambda self, *args, **kwargs: None):
                mapview = TUIMapView.__new__(TUIMapView)
                mapview.screen = mock_screen
                mapview.humanplayer = human
                mapview.debug = False
                mapview.run = Mock()
                mapview.run.get_accessible_locations.return_value = [Mock()]
                mapview.run.current_index = 0

                with patch('cardio.tui.mapview.get_keycode') as mock_keycode:
                    with patch.object(mapview, 'redraw'):
                        # Simulate: uppercase D key press, then Enter
                        mock_keycode.side_effect = [ord('D'), 13]
                        mapview.get_next_location()

                MockDeckExplorer.assert_called_once()
                mock_explorer_instance.show.assert_called_once()


class TestDeckExplorerRedraw:
    """Tests for redraw behavior to ensure no flickering."""

    def test_redraw_clears_buffer_once(self, mock_screen):
        from cardio.tui.deck_explorer import DeckExplorer

        deck = Deck("main", create_test_cards(3))
        collection = Deck("collection")

        explorer = DeckExplorer(deck=deck, collection=collection, screen=mock_screen)

        with patch('cardio.tui.deck_explorer.show_text'):
            with patch('cardio.tui.deck_explorer.show_card'):
                explorer.redraw(cursor=0)

        # clear_buffer should be called exactly once per redraw
        assert mock_screen.clear_buffer.call_count == 1

    def test_redraw_refreshes_once(self, mock_screen):
        from cardio.tui.deck_explorer import DeckExplorer

        deck = Deck("main", create_test_cards(3))
        collection = Deck("collection")

        explorer = DeckExplorer(deck=deck, collection=collection, screen=mock_screen)

        with patch('cardio.tui.deck_explorer.show_text'):
            with patch('cardio.tui.deck_explorer.show_card'):
                explorer.redraw(cursor=0)

        # refresh should be called exactly once per redraw
        assert mock_screen.refresh.call_count == 1
