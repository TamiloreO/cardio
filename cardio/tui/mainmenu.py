"""Main menu TUI for selecting game mode."""

from typing import Optional
from asciimatics.screen import Screen
from asciimatics.renderers import FigletText

from .tuibase import TUIBaseMixin
from .utils import show_text, get_keycode, splash_message, dPos
from .constants import Color


class GameMode:
    """Enum-like class for game modes."""

    COMPUTER = "computer"
    MULTIPLAYER = "multiplayer"


class TUIMainMenu(TUIBaseMixin):
    """Main menu for selecting between single player and multiplayer modes."""

    TITLE_POS = dPos(0, 3)
    MENU_POS = dPos(0, 20)

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.options = [
            ("vs Computer", GameMode.COMPUTER),
            ("vs Online Multiplayer (LAN)", GameMode.MULTIPLAYER),
        ]

    def show(self) -> Optional[str]:
        """Display the main menu and return the selected game mode."""
        cursor = 0

        while True:
            self._draw_menu(cursor)
            keycode = get_keycode(self.screen)

            if keycode == Screen.KEY_UP:
                cursor = max(0, cursor - 1)
            elif keycode == Screen.KEY_DOWN:
                cursor = min(len(self.options) - 1, cursor + 1)
            elif keycode in (13, Screen.KEY_ENTER):  # Enter
                return self.options[cursor][1]
            elif keycode == 27:  # Escape
                return None
            elif keycode in (ord("q"), ord("Q")):
                return None

    def _draw_menu(self, cursor: int) -> None:
        """Draw the main menu."""
        self.screen.clear_buffer(0, 0, 0)

        # Draw title
        title = str(FigletText("CARDIO", "big"))
        title_lines = title.split("\n")
        title_y = 3
        for line in title_lines:
            x = (self.screen.width - len(line)) // 2
            show_text(self.screen, dPos(x, title_y), line, color=Color.CYAN)
            title_y += 1

        # Draw subtitle
        subtitle = "A Card Battle Game"
        x = (self.screen.width - len(subtitle)) // 2
        show_text(self.screen, dPos(x, title_y + 1), subtitle, color=Color.GRAY)

        # Draw menu options
        menu_y = self.screen.height // 2
        for i, (label, _) in enumerate(self.options):
            if i == cursor:
                text = f"  > {label} <  "
                color = Color.YELLOW
            else:
                text = f"    {label}    "
                color = Color.WHITE

            x = (self.screen.width - len(text)) // 2
            show_text(self.screen, dPos(x, menu_y + i * 2), text, color=color)

        # Draw instructions
        instructions = "Use ↑↓ to select, Enter to confirm, Q to quit"
        x = (self.screen.width - len(instructions)) // 2
        show_text(
            self.screen,
            dPos(x, self.screen.height - 3),
            instructions,
            color=Color.GRAY,
        )

        self.screen.refresh()


class TUIMultiplayerMenu(TUIBaseMixin):
    """Menu for multiplayer options (host or join)."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.options = [
            ("Host Game", "host"),
            ("Join Game", "join"),
            ("Back", "back"),
        ]

    def show(self) -> Optional[str]:
        """Display the multiplayer menu and return the selected option."""
        cursor = 0

        while True:
            self._draw_menu(cursor)
            keycode = get_keycode(self.screen)

            if keycode == Screen.KEY_UP:
                cursor = max(0, cursor - 1)
            elif keycode == Screen.KEY_DOWN:
                cursor = min(len(self.options) - 1, cursor + 1)
            elif keycode in (13, Screen.KEY_ENTER):
                return self.options[cursor][1]
            elif keycode == 27:  # Escape
                return "back"

    def _draw_menu(self, cursor: int) -> None:
        """Draw the multiplayer menu."""
        self.screen.clear_buffer(0, 0, 0)

        # Title
        title = "MULTIPLAYER"
        x = (self.screen.width - len(title)) // 2
        show_text(self.screen, dPos(x, 5), title, color=Color.CYAN)

        # Menu options
        menu_y = self.screen.height // 2 - len(self.options)
        for i, (label, _) in enumerate(self.options):
            if i == cursor:
                text = f"  > {label} <  "
                color = Color.YELLOW
            else:
                text = f"    {label}    "
                color = Color.WHITE

            x = (self.screen.width - len(text)) // 2
            show_text(self.screen, dPos(x, menu_y + i * 2), text, color=color)

        # Instructions
        instructions = "Use ↑↓ to select, Enter to confirm, Esc to go back"
        x = (self.screen.width - len(instructions)) // 2
        show_text(
            self.screen,
            dPos(x, self.screen.height - 3),
            instructions,
            color=Color.GRAY,
        )

        self.screen.refresh()


class TUITextInput(TUIBaseMixin):
    """Simple text input dialog."""

    def __init__(self, prompt: str, default: str = "", *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.prompt = prompt
        self.text = default

    def show(self) -> Optional[str]:
        """Display the text input and return the entered text."""
        while True:
            self._draw_input()
            keycode = get_keycode(self.screen)

            if keycode is None:
                continue
            elif keycode in (13, Screen.KEY_ENTER):
                return self.text if self.text else None
            elif keycode == 27:  # Escape
                return None
            elif keycode == Screen.KEY_BACK or keycode == 127:  # Backspace
                self.text = self.text[:-1]
            elif 32 <= keycode <= 126:  # Printable ASCII
                self.text += chr(keycode)

    def _draw_input(self) -> None:
        """Draw the text input dialog."""
        self.screen.clear_buffer(0, 0, 0)

        # Prompt
        y = self.screen.height // 2 - 2
        x = (self.screen.width - len(self.prompt)) // 2
        show_text(self.screen, dPos(x, y), self.prompt, color=Color.WHITE)

        # Input box
        input_display = self.text + "_"
        box_width = max(40, len(input_display) + 4)
        x = (self.screen.width - box_width) // 2
        y += 3

        # Draw box border
        show_text(self.screen, dPos(x, y - 1), "┌" + "─" * (box_width - 2) + "┐")
        show_text(self.screen, dPos(x, y), "│" + " " * (box_width - 2) + "│")
        show_text(self.screen, dPos(x, y + 1), "└" + "─" * (box_width - 2) + "┘")

        # Draw input text
        text_x = x + 2
        show_text(self.screen, dPos(text_x, y), input_display, color=Color.YELLOW)

        # Instructions
        instructions = "Type your input, Enter to confirm, Esc to cancel"
        x = (self.screen.width - len(instructions)) // 2
        show_text(
            self.screen,
            dPos(x, self.screen.height - 3),
            instructions,
            color=Color.GRAY,
        )

        self.screen.refresh()
