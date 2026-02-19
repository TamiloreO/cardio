"""Hints widget for displaying game guide information on the TUI."""

from asciimatics.screen import Screen
from .utils import show_text, dPos
from .constants import Color

# Location markers and their descriptions
LOCATION_HINTS = """\
╔═══════════════════════════════════╗
║          LOCATION GUIDE           ║
╠═══════════════════════════════════╣
║ FFF  = Fight encounter            ║
║ ···  = Empty path (rest)          ║
║ UPU  = Upgrade power (+1)         ║
║ UHU  = Upgrade health (+1)        ║
║ UP*  = Risky power upgrade        ║
║ UH*  = Risky health upgrade       ║
║ S→→  = Transfer skill             ║
║ SL⚀  = Random skill lottery       ║
╠═══════════════════════════════════╣
║          CARD SYMBOLS             ║
╠═══════════════════════════════════╣
║ 💪  = Power (attack damage)       ║
║ 💓  = Health (hit points)         ║
║ 🔥  = Fire cost to play           ║
║ 👻  = Spirit cost to play         ║
╠═══════════════════════════════════╣
║           SKILLS                  ║
╠═══════════════════════════════════╣
║ 💀  = Instant Death               ║
║ 🐭  = Fertility (copy on play)    ║
║ 🪁  = Soaring (bypass cards)      ║
║ 🦔  = Spines (1 dmg on hit)       ║
║ 🚀  = Air Defense (blocks 🪁)     ║
║ 🔰  = Shield (absorbs 1 dmg)      ║
║ 🐩  = Underdog (+1 vs stronger)   ║
║ 🧺  = Packrat (draw on play)      ║
║ 🍀  = Lucky Strike (50/50 kill)   ║
║ 🩹  = Regenerate (heal 1/turn)    ║
║ 🤕  = Weakness (-1 damage)        ║
╠═══════════════════════════════════╣
║          CONTROLS                 ║
╠═══════════════════════════════════╣
║ ←/→  = Navigate options           ║
║ ↑/Enter = Confirm selection       ║
║ Esc  = Go back / Cancel           ║
╚═══════════════════════════════════╝\
"""


class HintsWidget:
    """Displays a guide/hints panel on the TUI."""

    def __init__(self, screen: Screen, pos: dPos) -> None:
        self.screen = screen
        self.pos = pos

    def show(self) -> None:
        show_text(self.screen, self.pos, LOCATION_HINTS, color=Color.GRAY)
