"""Help/Tutorial View with pagination support."""

import os
from typing import List, Tuple
import yaml
from asciimatics.screen import Screen
from .utils import show_text, get_keycode, dPos
from .constants import Color
from ..skills import get_skilltypes


def _generate_skills_list() -> str:
    """Dynamically generate skills list from skill types."""
    lines = []
    for skill_cls in get_skilltypes():
        skill = skill_cls()
        short_desc = skill.description.split('.')[0]
        lines.append(f"  {skill.symbol} {skill.name:14} - {short_desc}")
    return "\n".join(lines)


def _load_help_sections() -> List[Tuple[str, str]]:
    """Load help sections from YAML file."""
    yaml_path = os.path.join(os.path.dirname(__file__), "help_content.yaml")
    with open(yaml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    sections = []
    for section in data["sections"]:
        title = section["title"]
        content = section["content"]
        if section.get("generate_skills"):
            content = content.format(skills_list=_generate_skills_list())
        sections.append((title, content))
    return sections


HELP_SECTIONS = _load_help_sections()


class HelpView:
    """Paginated help/tutorial view."""

    HEADER_LINES = 2
    HIGHLIGHT_CHARS = ('💪', '💓', '🔥', '👻', '⚔', '🎰', '⬆', '🔄', '•')

    def __init__(self, screen: Screen) -> None:
        self.screen = screen
        self.current_page = 0
        self.total_pages = len(HELP_SECTIONS)

    def show(self) -> None:
        """Display the help view with pagination. Returns when user exits."""
        while True:
            self._draw_page()
            keycode = get_keycode(self.screen)

            if keycode == Screen.KEY_RIGHT or keycode == ord('n'):
                self.current_page = min(self.current_page + 1, self.total_pages - 1)
            elif keycode == Screen.KEY_LEFT or keycode == ord('p'):
                self.current_page = max(self.current_page - 1, 0)
            elif keycode == Screen.KEY_HOME:
                self.current_page = 0
            elif keycode == Screen.KEY_END:
                self.current_page = self.total_pages - 1
            elif keycode in (Screen.KEY_ESCAPE, ord('h'), ord('H'), ord('q'), ord('Q')):
                break
            elif keycode == 13:
                if self.current_page < self.total_pages - 1:
                    self.current_page += 1
                else:
                    break

    def _get_line_color(self, line: str, line_idx: int) -> Color:
        """Determine color for a line."""
        if line_idx < self.HEADER_LINES or line.startswith('==='):
            return Color.YELLOW
        stripped = line.strip()
        if any(stripped.startswith(c) for c in self.HIGHLIGHT_CHARS):
            return Color.CYAN
        return Color.WHITE

    def _draw_page(self) -> None:
        self.screen.clear_buffer(0, 0, 0)
        title, content = HELP_SECTIONS[self.current_page]

        margin_x, margin_y = 4, 2
        for i, line in enumerate(content.split('\n')):
            if margin_y + i >= self.screen.height - 4:
                break
            color = self._get_line_color(line, i)
            show_text(self.screen, dPos(margin_x, margin_y + i), line, color=color)

        footer_y = self.screen.height - 2
        page_info = f"Page {self.current_page + 1} of {self.total_pages}: {title}"
        nav_info = "← Previous | Next → | Enter: Continue | Esc/Q: Close"

        show_text(self.screen, dPos(margin_x, footer_y - 1), page_info, color=Color.YELLOW)
        show_text(self.screen, dPos(margin_x, footer_y), nav_info, color=Color.GRAY)

        dots = " ".join("●" if i == self.current_page else "○" for i in range(self.total_pages))
        show_text(self.screen, dPos(self.screen.width - len(dots) - 4, footer_y - 1),
                  dots, color=Color.MAGENTA)

        self.screen.refresh()


def show_help(screen: Screen) -> None:
    """Convenience function to show help view."""
    HelpView(screen).show()
