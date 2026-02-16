"""Main menu screen for the game."""

from enum import Enum, auto
from asciimatics.renderers import FigletText
from asciimatics.screen import Screen
from .tuibase import TUIBaseMixin
from .utils import show_text, show, dPos, get_keycode
from .constants import Color


class MenuChoice(Enum):
    CONTINUE = auto()
    NEW_GAME = auto()
    EXIT = auto()


class MainMenu(TUIBaseMixin):
    def __init__(self, has_save: bool = False, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.has_save = has_save

    def show_menu(self) -> MenuChoice:
        menu_items = []
        if self.has_save:
            menu_items.append(("Continue Game", MenuChoice.CONTINUE))
        menu_items.append(("New Game", MenuChoice.NEW_GAME))
        menu_items.append(("Exit", MenuChoice.EXIT))

        cursor = 0
        while True:
            self.screen.clear_buffer(0, 0, 0)

            # Render title with FigletText
            title = FigletText("CARDIO", "banner3-D")
            title_str = str(title)
            title_lines = title_str.split("\n")
            title_width = max(len(line) for line in title_lines)
            title_x = (self.screen.width - title_width) // 2
            title_y = 5

            show(self.screen, dPos(title_x, title_y), title, Color.RED)

            # Menu items
            menu_y = title_y + len(title_lines) + 4
            for i, (label, _) in enumerate(menu_items):
                if i == cursor:
                    text = f"> {label} <"
                    color = Color.YELLOW
                else:
                    text = f"  {label}"
                    color = Color.WHITE
                x = (self.screen.width - len(text)) // 2
                show_text(self.screen, dPos(x, menu_y + i * 2), text, color)

            # Instructions
            instructions = "Use UP/DOWN to navigate, ENTER to select"
            show_text(
                self.screen,
                dPos((self.screen.width - len(instructions)) // 2, menu_y + len(menu_items) * 2 + 3),
                instructions,
                Color.GRAY,
            )

            self.screen.refresh()

            keycode = get_keycode(self.screen)
            if keycode == Screen.KEY_UP:
                cursor = (cursor - 1) % len(menu_items)
            elif keycode == Screen.KEY_DOWN:
                cursor = (cursor + 1) % len(menu_items)
            elif keycode == 13:  # Enter
                self.close()
                return menu_items[cursor][1]
