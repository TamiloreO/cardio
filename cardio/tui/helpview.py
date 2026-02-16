"""Help/Tutorial View with pagination support."""

from pathlib import Path
from typing import List, Tuple
import yaml
from asciimatics.screen import Screen

from cardio.skills import get_skilltypes
from .utils import show_text, get_keycode, dPos
from .constants import Color


def _generate_skills_content() -> str:
    """Generate skills section dynamically from registered skill types."""
    lines = [
        "SKILLS - Special Abilities",
        "==========================",
        "",
        "Cards can have special skills shown as emoji symbols:",
        "",
    ]
    for skill_cls in get_skilltypes():
        skill = skill_cls()
        # Truncate description to fit on screen
        desc = skill.description.split('.')[0]  # First sentence only
        lines.append(f"  {skill.symbol} {skill.name:14} - {desc}")
    
    lines.extend(["", "Skills can combine in interesting ways - experiment!"])
    return "\n".join(lines)


def _load_help_sections() -> List[Tuple[str, str]]:
    """Load help sections from YAML file, with dynamic skill generation."""
    yaml_path = Path(__file__).parent / "help_content.yaml"
    with open(yaml_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    
    sections = []
    for section in data['sections']:
        title = section['title']
        content = section['content']
        # Generate skills content dynamically
        if title == "Skills" and content is None:
            content = _generate_skills_content()
        sections.append((title, content))
    
    return sections


class HelpView:
    """Paginated help/tutorial view."""

    def __init__(self, screen: Screen) -> None:
        self.screen = screen
        self.sections = _load_help_sections()
        self.current_page = 0
        self.total_pages = len(self.sections)

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
            elif keycode == 13:  # Enter - go to next or exit on last page
                if self.current_page < self.total_pages - 1:
                    self.current_page += 1
                else:
                    break

    def _get_line_color(self, line: str, line_index: int) -> Color:
        """Determine line color based on content."""
        stripped = line.strip()
        # Headers (first two lines or separator lines)
        if line_index < 2 or stripped.startswith('==='):
            return Color.YELLOW
        # Lines starting with emoji or bullet points
        if stripped and stripped[0] in '💪💓🔥👻💀🐭🪁🦔🚀🔰🐩🧺🍀🩹🤕⚔🎰⬆🔄•':
            return Color.CYAN
        return Color.WHITE

    def _draw_page(self) -> None:
        self.screen.clear_buffer(0, 0, 0)

        title, content = self.sections[self.current_page]

        # Draw content
        margin_x, margin_y = 4, 2
        for i, line in enumerate(content.split('\n')):
            if margin_y + i >= self.screen.height - 4:
                break
            color = self._get_line_color(line, i)
            show_text(self.screen, dPos(margin_x, margin_y + i), line, color=color)

        # Draw navigation footer
        footer_y = self.screen.height - 2
        page_info = f"Page {self.current_page + 1} of {self.total_pages}: {title}"
        nav_info = "← Previous | Next → | Enter: Continue | Esc/Q: Close"

        show_text(self.screen, dPos(margin_x, footer_y - 1), page_info, color=Color.YELLOW)
        show_text(self.screen, dPos(margin_x, footer_y), nav_info, color=Color.GRAY)

        # Draw page indicator dots
        dots = " ".join("●" if i == self.current_page else "○" for i in range(self.total_pages))
        show_text(self.screen, dPos(self.screen.width - len(dots) - 4, footer_y - 1),
                  dots, color=Color.MAGENTA)

        self.screen.refresh()


def show_help(screen: Screen) -> None:
    """Convenience function to show help view."""
    help_view = HelpView(screen)
    help_view.show()
