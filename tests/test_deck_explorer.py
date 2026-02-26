"""Tests for DeckExplorer functionality.

These tests verify the core logic of DeckExplorer without requiring
a working terminal/screen. The tests mock the screen and UI components.

Note: These tests require asciimatics >= 1.14.0 for SINGLE_LINE/DOUBLE_LINE constants.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

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
        assert explorer._owns_screen is False

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

    def test_init_passes_screen_to_parent(self, mock_screen):
        """Verify that screen is passed to TUIBaseMixin.__init__()."""
        from cardio.tui.deck_explorer import DeckExplorer

        deck = Deck("main", create_test_cards(1))
        collection = Deck("collection")

        explorer = DeckExplorer(
            deck=deck,
            collection=collection,
            screen=mock_screen,
        )

        # TUIBaseMixin sets _owns_screen based on whether screen was provided
        assert explorer._owns_screen is False
        assert explorer.screen is mock_screen


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
        explorer.scroll_offset = 5

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

        deck = Deck("main", create_test_cards(50))
        collection = Deck("collection")

        explorer = DeckExplorer(deck=deck, collection=collection, screen=mock_screen)
        explorer.cards_per_row = 5
        explorer.visible_rows = 2

        # Cursor at row 0, scroll should be 0
        explorer._adjust_scroll_for_cursor(0)
        assert explorer.scroll_offset == 0

        # Cursor at row 2 (beyond visible), scroll should adjust
        explorer._adjust_scroll_for_cursor(10)  # Row 2 (10 // 5 = 2)
        assert explorer.scroll_offset == 1  # Should show rows 1-2

    def test_scroll_offset_adjusts_when_cursor_moves_up(self, mock_screen):
        from cardio.tui.deck_explorer import DeckExplorer

        deck = Deck("main", create_test_cards(50))
        collection = Deck("collection")

        explorer = DeckExplorer(deck=deck, collection=collection, screen=mock_screen)
        explorer.cards_per_row = 5
        explorer.visible_rows = 2
        explorer.scroll_offset = 5

        # Move cursor to row 3 (before current scroll)
        explorer._adjust_scroll_for_cursor(15)  # Row 3
        assert explorer.scroll_offset == 3

    def test_get_total_rows_calculation(self, mock_screen):
        from cardio.tui.deck_explorer import DeckExplorer

        deck = Deck("main", create_test_cards(17))
        collection = Deck("collection")

        explorer = DeckExplorer(deck=deck, collection=collection, screen=mock_screen)
        explorer.cards_per_row = 5

        # 17 cards / 5 per row = 4 rows (ceil)
        assert explorer._get_total_rows() == 4

    def test_get_total_rows_empty_deck(self, mock_screen):
        from cardio.tui.deck_explorer import DeckExplorer

        deck = Deck("main")
        collection = Deck("collection")

        explorer = DeckExplorer(deck=deck, collection=collection, screen=mock_screen)

        assert explorer._get_total_rows() == 0

    def test_switch_tab_resets_scroll(self, mock_screen):
        from cardio.tui.deck_explorer import DeckExplorer

        deck = Deck("main", create_test_cards(50))
        collection = Deck("collection", create_test_cards(30))

        explorer = DeckExplorer(deck=deck, collection=collection, screen=mock_screen)
        explorer.scroll_offset = 10

        explorer._switch_tab(to_deck=False)

        assert explorer.scroll_offset == 0


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
        assert explorer._owns_screen is False

        explorer.close()

        # screen.close() should NOT have been called since we borrowed the screen
        mock_screen.close.assert_not_called()


class TestMapViewDeckExplorerIntegration:
    """Tests for opening deck explorer from map view."""

    def test_d_key_opens_deck_explorer_from_mapview(self, mock_screen):
        """Test that pressing D key in map view's get_next_location opens the deck explorer."""
        with patch('cardio.tui.mapview.DeckExplorer') as MockDeckExplorer:
            mock_explorer_instance = Mock()
            MockDeckExplorer.return_value = mock_explorer_instance

            from cardio.tui.mapview import TUIMapView
            from cardio import HumanPlayer, Deck
            from cardio.run import Run
            from asciimatics.screen import Screen

            # Create minimal test setup
            human = HumanPlayer(name="Test")
            human.deck = Deck("main", create_test_cards(3))
            human.collection = Deck("collection", create_test_cards(5))

            # Create a mock run with accessible locations
            mock_run = Mock(spec=Run)
            mock_location = Mock()
            mock_location.marker = "X"
            mock_run.get_accessible_locations.return_value = [mock_location]
            mock_run.current_index = 0

            with patch.object(TUIMapView, '__init__', lambda self, *args, **kwargs: None):
                mapview = TUIMapView.__new__(TUIMapView)
                mapview.screen = mock_screen
                mapview.humanplayer = human
                mapview.run = mock_run
                mapview.debug = False
                mapview.humanstate = Mock()
                mapview.MAPTOPLEFT = Mock()
                mapview.GAMEINFO = Mock()
                
                # Mock redraw to avoid complex rendering
                mapview.redraw = Mock()

                with patch('cardio.tui.mapview.get_keycode') as mock_keycode:
                    # Simulate: D key (opens explorer), then UP key (selects location)
                    mock_keycode.side_effect = [ord('d'), Screen.KEY_UP]
                    
                    result = mapview.get_next_location()

                # Verify DeckExplorer was created with correct arguments
                MockDeckExplorer.assert_called_once()
                call_kwargs = MockDeckExplorer.call_args[1]
                assert call_kwargs['deck'] is human.deck
                assert call_kwargs['collection'] is human.collection
                assert call_kwargs['screen'] is mock_screen

                # Verify show() was called on the explorer
                mock_explorer_instance.show.assert_called_once()

                # Verify the location was returned after pressing UP
                assert result == mock_location

    def test_lowercase_d_also_opens_explorer(self, mock_screen):
        """Test that lowercase 'd' also opens the deck explorer."""
        with patch('cardio.tui.mapview.DeckExplorer') as MockDeckExplorer:
            mock_explorer_instance = Mock()
            MockDeckExplorer.return_value = mock_explorer_instance

            from cardio.tui.mapview import TUIMapView
            from cardio import HumanPlayer, Deck
            from cardio.run import Run
            from asciimatics.screen import Screen

            human = HumanPlayer(name="Test")
            human.deck = Deck("main", create_test_cards(3))
            human.collection = Deck("collection", create_test_cards(5))

            mock_run = Mock(spec=Run)
            mock_location = Mock()
            mock_run.get_accessible_locations.return_value = [mock_location]
            mock_run.current_index = 0

            with patch.object(TUIMapView, '__init__', lambda self, *args, **kwargs: None):
                mapview = TUIMapView.__new__(TUIMapView)
                mapview.screen = mock_screen
                mapview.humanplayer = human
                mapview.run = mock_run
                mapview.debug = False
                mapview.humanstate = Mock()
                mapview.MAPTOPLEFT = Mock()
                mapview.GAMEINFO = Mock()
                mapview.redraw = Mock()

                with patch('cardio.tui.mapview.get_keycode') as mock_keycode:
                    # Use lowercase 'd'
                    mock_keycode.side_effect = [ord('D'), 13]  # D then Enter
                    
                    mapview.get_next_location()

                MockDeckExplorer.assert_called_once()
                mock_explorer_instance.show.assert_called_once()
