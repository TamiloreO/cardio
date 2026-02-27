"""cardio.tui.menu_constants — Static menu item definitions.

Extracted into a zero-import module so that tests can inspect menu content without
triggering the asciimatics TUI import chain.
"""

from __future__ import annotations

from typing import List, Literal

# String labels shown for each option (index-aligned with TOKENS).
ITEMS: List[str] = [
    "  vs Computer  ",
    "  vs LAN Multiplayer  ",
    "  Exit  ",
]

# Return tokens for each option (index-aligned with ITEMS).
TOKENS: List[Literal["computer", "multiplayer", "exit"]] = [
    "computer",
    "multiplayer",
    "exit",
]
