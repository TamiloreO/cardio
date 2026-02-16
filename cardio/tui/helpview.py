from typing import List
from asciimatics.screen import Screen
from .utils import show_text, dPos, get_keycode
from .constants import Color
from ..skills import get_skilltypes


HELP_PAGES = [
    {
        "title": "Welcome to Cardio! (1/5)",
        "content": """
Cardio is a card battling game where you fight against the computer.

CONTROLS:
  Arrow Keys  - Navigate / Move cursor
  Enter       - Select / Confirm
  Escape      - Cancel / Go back
  C           - End turn during fights
  H           - Open this help menu
  $           - Quit game

OBJECTIVE:
  Defeat the computer by dealing damage to reduce their lives to zero.
  Don't let the computer do the same to you!

Press LEFT/RIGHT to navigate pages, ESCAPE to close help.
"""
    },
    {
        "title": "Card Basics (2/5)",
        "content": """
Each card has these attributes:

  💪 POWER    - How much damage the card deals when attacking
  💓 HEALTH   - How much damage the card can take before dying

Cards are placed on a grid. Your cards (bottom) fight against
the computer's cards (top). Each round:
  1. Computer places cards
  2. You place cards from your hand
  3. Cards attack the opposing card or the opponent directly

When a card's health reaches 0, it dies and is removed from play.
"""
    },
    {
        "title": "Fire & Spirits (3/5)",
        "content": """
To play cards, you need resources: FIRE 🔥 or SPIRITS 👻

COSTS (shown bottom-right of card):
  🔥 Fire Cost    - Sacrifice cards on the field to generate fire
  👻 Spirit Cost  - Spend spirits you've accumulated

PROVIDES (shown bottom-left of card):
  First number  = Fire value when sacrificed (default: 1)
  Second number = Spirits generated when card dies (default: 1)

  "_" means the card provides 0 of that resource
  Numbers other than 1 are displayed explicitly

EXAMPLE:
  A card showing "2 _" provides 2 fire when sacrificed, 0 spirits on death
  A card with 🔥🔥 cost needs 2 fire (sacrifice cards worth 2+ fire)

Free cards (0 cost) can be played without any resources!
"""
    },
    {
        "title": "Skills (4/5)",
        "content": ""
    },
    {
        "title": "Skills Continued (5/5)",
        "content": ""
    },
]


def _build_skill_pages() -> None:
    skills = get_skilltypes()
    skills_text_1 = "Cards can have special abilities (skills):\n\n"
    skills_text_2 = "More skills:\n\n"
    
    half = (len(skills) + 1) // 2
    for i, skill_cls in enumerate(skills):
        s = skill_cls()
        line = f"  {s.symbol} {s.name}: {s.description[:60]}"
        if len(s.description) > 60:
            line += "..."
        line += "\n"
        if i < half:
            skills_text_1 += line
        else:
            skills_text_2 += line
    
    HELP_PAGES[3]["content"] = skills_text_1
    HELP_PAGES[4]["content"] = skills_text_2

_build_skill_pages()


class HelpView:
    def __init__(self, screen: Screen) -> None:
        self.screen = screen
        self.current_page = 0
    
    def show(self) -> None:
        while True:
            self._draw_page()
            keycode = get_keycode(self.screen)
            if keycode == Screen.KEY_ESCAPE:
                break
            elif keycode == Screen.KEY_LEFT:
                self.current_page = max(0, self.current_page - 1)
            elif keycode == Screen.KEY_RIGHT:
                self.current_page = min(len(HELP_PAGES) - 1, self.current_page + 1)
    
    def _draw_page(self) -> None:
        self.screen.clear_buffer(0, 0, 0)
        page = HELP_PAGES[self.current_page]
        
        # Title
        title_x = self.screen.width // 2 - len(page["title"]) // 2
        show_text(self.screen, dPos(title_x, 2), page["title"], Color.YELLOW)
        
        # Content
        lines = page["content"].split("\n")
        y = 5
        for line in lines:
            show_text(self.screen, dPos(10, y), line, Color.WHITE)
            y += 1
        
        # Navigation hints
        nav = "< LEFT | RIGHT >  |  ESC to close"
        nav_x = self.screen.width // 2 - len(nav) // 2
        show_text(self.screen, dPos(nav_x, self.screen.height - 3), nav, Color.GRAY)
        
        self.screen.refresh()
