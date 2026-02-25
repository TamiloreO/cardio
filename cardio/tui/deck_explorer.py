from typing import List, Literal, Optional
from asciimatics.screen import Screen
from .utils import get_keycode, dPos, show_text
from .card_primitives import VisualState, show_card, BOX_WIDTH, BOX_PADDING_LEFT, BOX_HEIGHT, BOX_PADDING_TOP
from .constants import Color
from cardio import Card, Deck


class DeckExplorer:
    """Displays cards from multiple decks with tab switching and scrolling."""
    
    TAB_HEIGHT = 3
    HEADER_Y = 1
    CARDS_START_Y = TAB_HEIGHT + 2
    
    def __init__(self, screen: Screen, decks: List[Deck]) -> None:
        self.screen = screen
        self.decks = decks
        self.active_tab = 0
        self.scroll_offset = 0
        self.cursor = 0
        
        self.gross_width = BOX_WIDTH + BOX_PADDING_LEFT
        self.gross_height = BOX_HEIGHT + BOX_PADDING_TOP
        self.cards_per_row = max(1, (self.screen.width - 4) // self.gross_width)
        self.visible_rows = max(1, (self.screen.height - self.CARDS_START_Y - 4) // self.gross_height)
        self.cards_per_page = self.cards_per_row * self.visible_rows
        
    @property
    def current_deck(self) -> Deck:
        return self.decks[self.active_tab]
    
    @property
    def current_cards(self) -> List[Card]:
        return self.current_deck.cards
    
    def card_pos(self, index: int) -> Optional[dPos]:
        adjusted = index - self.scroll_offset * self.cards_per_row
        if adjusted < 0 or adjusted >= self.cards_per_page:
            return None
        row = adjusted // self.cards_per_row
        col = adjusted % self.cards_per_row
        x = 2 + col * self.gross_width
        y = self.CARDS_START_Y + row * self.gross_height
        return dPos(x, y)
    
    def draw_tabs(self) -> None:
        x = 2
        for i, deck in enumerate(self.decks):
            label = f" {deck.name} ({deck.size()}) "
            if i == self.active_tab:
                show_text(self.screen, dPos(x, self.HEADER_Y), f"[{label}]", Color.CYAN)
            else:
                show_text(self.screen, dPos(x, self.HEADER_Y), f" {label} ", Color.GRAY)
            x += len(label) + 4
        
        hint = "←/→: switch tabs | ↑/↓: navigate | ESC/D: close"
        show_text(self.screen, dPos(2, self.HEADER_Y + 1), hint, Color.GRAY)
    
    def draw_cards(self) -> None:
        cards = self.current_cards
        if not cards:
            show_text(
                self.screen, 
                dPos(self.screen.width // 2 - 10, self.screen.height // 2),
                "(No cards in this deck)",
                Color.GRAY
            )
            return
            
        start = self.scroll_offset * self.cards_per_row
        end = min(start + self.cards_per_page, len(cards))
        
        for i in range(start, end):
            pos = self.card_pos(i)
            if pos:
                state = VisualState.CURSOR if i == self.cursor else VisualState.NORMAL
                show_card(self.screen, cards[i], pos, state)
        
        total_rows = (len(cards) + self.cards_per_row - 1) // self.cards_per_row
        if total_rows > self.visible_rows:
            scroll_info = f"Page {self.scroll_offset + 1}/{total_rows - self.visible_rows + 1}"
            show_text(
                self.screen, 
                dPos(self.screen.width - len(scroll_info) - 2, self.screen.height - 2),
                scroll_info,
                Color.GRAY
            )
    
    def redraw(self) -> None:
        self.screen.clear_buffer(0, 0, 0)
        self.draw_tabs()
        self.draw_cards()
        self.screen.refresh()
    
    def ensure_cursor_visible(self) -> None:
        if not self.current_cards:
            self.cursor = 0
            self.scroll_offset = 0
            return
            
        self.cursor = max(0, min(self.cursor, len(self.current_cards) - 1))
        cursor_row = self.cursor // self.cards_per_row
        
        if cursor_row < self.scroll_offset:
            self.scroll_offset = cursor_row
        elif cursor_row >= self.scroll_offset + self.visible_rows:
            self.scroll_offset = cursor_row - self.visible_rows + 1
    
    def switch_tab(self, direction: Literal[-1, 1]) -> None:
        self.active_tab = (self.active_tab + direction) % len(self.decks)
        self.cursor = 0
        self.scroll_offset = 0
    
    def move_cursor(self, direction: str) -> None:
        if not self.current_cards:
            return
            
        if direction == "left":
            self.cursor = max(0, self.cursor - 1)
        elif direction == "right":
            self.cursor = min(len(self.current_cards) - 1, self.cursor + 1)
        elif direction == "up":
            new_cursor = self.cursor - self.cards_per_row
            if new_cursor >= 0:
                self.cursor = new_cursor
        elif direction == "down":
            new_cursor = self.cursor + self.cards_per_row
            if new_cursor < len(self.current_cards):
                self.cursor = new_cursor
        
        self.ensure_cursor_visible()
    
    def run(self) -> None:
        self.ensure_cursor_visible()
        while True:
            self.redraw()
            keycode = get_keycode(self.screen)
            
            if keycode in (Screen.KEY_ESCAPE, ord('d'), ord('D')):
                break
            elif keycode == Screen.KEY_TAB:
                self.switch_tab(1)
            elif keycode == Screen.KEY_LEFT:
                if self.cursor % self.cards_per_row == 0:
                    self.switch_tab(-1)
                else:
                    self.move_cursor("left")
            elif keycode == Screen.KEY_RIGHT:
                if (self.cursor + 1) % self.cards_per_row == 0 or self.cursor == len(self.current_cards) - 1:
                    self.switch_tab(1)
                else:
                    self.move_cursor("right")
            elif keycode == Screen.KEY_UP:
                self.move_cursor("up")
            elif keycode == Screen.KEY_DOWN:
                self.move_cursor("down")
