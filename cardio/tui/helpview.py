"""Help/Tutorial View with pagination support."""

from typing import List, Tuple
from asciimatics.screen import Screen
from .utils import show_text, get_keycode, dPos
from .constants import Color


HELP_SECTIONS: List[Tuple[str, str]] = [
    ("Overview", """\
CARDIO - Card Battle Game
=========================

Welcome to Cardio! This is a card battling game where you fight against
computer opponents using a deck of creature cards.

Your goal is to survive as many fights as possible, building up your
deck and resources along the way.

Navigation:
  Arrow Keys  - Move cursor / Navigate
  Enter       - Confirm selection
  Escape      - Cancel / Go back
  H           - Open this help (from map view)
  $           - Emergency exit (anytime)
"""),

    ("Cards Basics", """\
CARDS - Basic Attributes
========================

Each card has the following basic attributes:

  💪 Power    - How much damage the card deals when attacking
  💓 Health   - How much damage the card can take before dying

Cards are displayed in boxes showing:
  - Name at the top
  - Power (💪) and Health (💓) symbols
  - Skills as emoji symbols
  - Cost and resource info at the bottom (for your cards)

During a fight, your cards attack the opposing cards. If there's no
opposing card, the attack hits the opponent directly!
"""),

    ("Fire & Spirits", """\
FIRE & SPIRITS - Card Resources
===============================

Cards have TWO types of resources for playing them:

🔥 FIRE (costs_fire / has_fire)
  - Some cards COST fire to play (shown in bottom-right: 🔥)
  - To pay fire cost, you must SACRIFICE other cards on your field
  - Each card HAS a fire value (usually 1) shown in bottom-left
  - Sacrifice enough cards to meet the fire cost

👻 SPIRITS (costs_spirits / has_spirits)  
  - Some cards COST spirits to play (shown in bottom-right: 👻)
  - Spirits come from your spirit pool (shown in player stats)
  - When your cards DIE, they add spirits to your pool
  - Each card HAS a spirit value (usually 1)

Bottom-left of card shows: [fire_value] [spirit_value]
  - "_" means 0 (no fire/spirits provided)
  - A number shows how much fire/spirits the card provides
  - Values of 1 are shown as a space (most common default)
"""),

    ("Playing Cards", """\
PLAYING CARDS - How to Place
============================

During your turn in a fight:

1. SELECT a card from your hand (bottom row) using arrow keys
2. Press UP or ENTER to start placing it

If the card costs FIRE (🔥):
  - First, MARK cards to sacrifice (press DOWN/ENTER on field cards)
  - Marked cards will be highlighted in blue
  - Keep marking until you have enough fire
  - Then pick where to place (empty slot or marked slot)

If the card costs SPIRITS (👻):
  - Just pick an empty slot - spirits are deducted automatically

If the card costs NOTHING:
  - Called "Hamster cards" - just pick an empty slot!

Press C when done placing cards to continue the fight.
"""),

    ("Skills", """\
SKILLS - Special Abilities
==========================

Cards can have special skills shown as emoji symbols:

  💀 Instant Death  - Instantly kills any card it damages
  🐭 Fertility      - Creates a copy in your hand when played
  🪁 Soaring        - Ignores opposing cards, hits opponent directly
  🦔 Spines         - Attacker takes 1 damage after attacking
  🚀 Air Defense    - Blocks Soaring attacks
  🔰 Shield         - Absorbs 1 damage per turn
  🐩 Underdog       - +1 power when facing stronger opponent
  🧺 Packrat        - Draw a card when played
  🍀 Lucky Strike   - 50/50 chance: instant kill or self-destruct
  🩹 Regenerate     - Heals 1 damage at end of each round
  🤕 Weakness       - Deals 1 less damage (negative skill)

Skills can combine in interesting ways - experiment!
"""),

    ("Fight Mechanics", """\
FIGHT MECHANICS
===============

The battlefield has 4 rows:
  Row 0: Computer's preparation row (cards wait here)
  Row 1: Computer's active row (cards attack from here)
  ----  Gap between players
  Row 2: Your active row (your cards attack from here)
  Row 3: Your hand (cards you can play)

Each round:
  1. Computer places/moves cards
  2. You place cards and press C to continue
  3. All cards in active rows attack simultaneously
  4. Damage is dealt, cards may die
  5. Dead cards go to discard, generate spirits

Win by dealing enough damage to the opponent!
Lose if you take too much damage or run out of cards.
"""),

    ("Decks & Drawing", """\
DECKS & DRAWING
===============

During a fight, you have multiple decks:

  Draw Deck     - Your main deck, draw from here
  Hamster Deck  - Special free cards (0 cost)
  Hand          - Cards you can currently play
  Discard       - Used/dead cards go here

At the start of your turn, choose which deck to draw from
using LEFT/RIGHT arrows, then UP/ENTER to draw.

The draw deck contains your actual cards.
The hamster deck contains free "hamster" cards that cost nothing
to play but are weaker.

Manage your resources carefully!
"""),

    ("Map & Locations", """\
MAP & LOCATIONS
===============

Between fights, you navigate a map with various locations:

  ⚔️  Fight     - Battle against computer opponent
  🎰 Lottery   - Chance to win new cards or skills
  ⬆️  Upgrader  - Improve your existing cards
  🔄 Transfer  - Move skills between cards

Use arrow keys to choose your path and ENTER to move.

Your progress is shown by the current "rung" - how far
you've traveled from the start.

The game auto-saves after each location!
"""),

    ("Tips & Strategy", """\
TIPS & STRATEGY
===============

• Balance your deck - mix high-cost powerful cards with
  cheap cards you can sacrifice for fire

• Cards with 0 fire cost are valuable - save them!

• Build up spirits by letting cards die strategically

• Air Defense counters Soaring - watch for flying enemies

• Shield is powerful against multiple weak attacks

• Regenerate helps cards survive longer battles

• Fertility cards multiply - great value over time

• Watch the deadlock counter - stalemates end badly!

Good luck, and may your cards serve you well! 🎴
"""),
]


class HelpView:
    """Paginated help/tutorial view."""

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
            elif keycode == 13:  # Enter - go to next or exit on last page
                if self.current_page < self.total_pages - 1:
                    self.current_page += 1
                else:
                    break

    def _draw_page(self) -> None:
        self.screen.clear_buffer(0, 0, 0)

        title, content = HELP_SECTIONS[self.current_page]

        # Draw content
        margin_x, margin_y = 4, 2
        for i, line in enumerate(content.split('\n')):
            if margin_y + i >= self.screen.height - 4:
                break
            # Highlight the title/header lines
            if i < 2 or line.startswith('==='):
                color = Color.YELLOW
            elif line.strip().startswith(('💪', '💓', '🔥', '👻', '💀', '🐭', '🪁', '🦔',
                                          '🚀', '🔰', '🐩', '🧺', '🍀', '🩹', '🤕', '⚔',
                                          '🎰', '⬆', '🔄', '•')):
                color = Color.CYAN
            else:
                color = Color.WHITE
            show_text(self.screen, dPos(margin_x, margin_y + i), line, color=color)

        # Draw navigation footer
        footer_y = self.screen.height - 2
        page_info = f"Page {self.current_page + 1} of {self.total_pages}: {title}"
        nav_info = "← Previous | Next → | Enter: Continue | Esc/Q: Close"

        show_text(self.screen, dPos(margin_x, footer_y - 1), page_info, color=Color.YELLOW)
        show_text(self.screen, dPos(margin_x, footer_y), nav_info, color=Color.GRAY)

        # Draw page indicator dots
        dots = ""
        for i in range(self.total_pages):
            if i == self.current_page:
                dots += "● "
            else:
                dots += "○ "
        show_text(self.screen, dPos(self.screen.width - len(dots) - 4, footer_y - 1),
                  dots, color=Color.MAGENTA)

        self.screen.refresh()


def show_help(screen: Screen) -> None:
    """Convenience function to show help view."""
    help_view = HelpView(screen)
    help_view.show()
