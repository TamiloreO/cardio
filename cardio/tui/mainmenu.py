from typing import Optional, Literal
from asciimatics.screen import Screen
from asciimatics.renderers import FigletText
from .utils import show_text, get_keycode, dPos, show
from .constants import Color
from .tuibase import TUIBaseMixin


MenuChoice = Literal["continue", "start", "exit"]


class MainMenu(TUIBaseMixin):
    TITLE_POS = dPos(0, 2)
    MENU_POS = dPos(0, 14)

    def __init__(self, has_save: bool = False, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.has_save = has_save
        self.menu_items: list[tuple[str, MenuChoice]] = []
        if has_save:
            self.menu_items.append(("Continue Game", "continue"))
        self.menu_items.append(("Start New Game", "start"))
        self.menu_items.append(("Exit Game", "exit"))

    def _draw_title(self) -> None:
        figlet = FigletText("CARDIO", "banner3-D")
        figlet_str = str(figlet)
        lines = figlet_str.split("\n")
        max_width = max(len(line) for line in lines)
        x = (self.screen.width - max_width) // 2
        for i, line in enumerate(lines):
            show_text(self.screen, dPos(x, self.TITLE_POS.y + i), line, color=Color.RED)

    def _draw_menu(self, cursor: int) -> None:
        menu_y = self.MENU_POS.y
        for i, (label, _) in enumerate(self.menu_items):
            if i == cursor:
                text = f"> {label} <"
                color = Color.YELLOW
            else:
                text = f"  {label}"
                color = Color.WHITE
            x = (self.screen.width - len(text)) // 2
            show_text(self.screen, dPos(x, menu_y + i * 2), text, color=color)

    def redraw(self, cursor: int) -> None:
        self.screen.clear_buffer(0, 0, 0)
        self._draw_title()
        self._draw_menu(cursor)
        # Instructions at bottom
        instructions = "Use UP/DOWN to navigate, ENTER to select"
        x = (self.screen.width - len(instructions)) // 2
        show_text(self.screen, dPos(x, self.screen.height - 3), instructions, color=Color.GRAY)
        self.screen.refresh()

    def show(self) -> MenuChoice:
        cursor = 0
        while True:
            self.redraw(cursor)
            keycode = get_keycode(self.screen)
            if keycode == Screen.KEY_UP:
                cursor = max(0, cursor - 1)
            elif keycode == Screen.KEY_DOWN:
                cursor = min(len(self.menu_items) - 1, cursor + 1)
            elif keycode == 13:  # Enter
                self.close()
                return self.menu_items[cursor][1]
