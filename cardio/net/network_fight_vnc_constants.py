"""cardio.net.network_fight_vnc_constants — Turn-hint layout constants.

Extracted into a zero-import module so that tests can verify the hint position and
clear-string length without triggering the asciimatics TUI import chain.

``HINT_POS`` is a plain ``(x, y)`` tuple so this module has no dependencies at all.
``network_fight_vnc.py`` wraps it with ``dPos()`` at the point of use.
"""

from __future__ import annotations

# Screen position for the turn-status hint as a plain (x, y) tuple.
# Row 1, column 1 — above the fight grid (which starts at row 4) and never
# overwritten by the normal fight renderer.
HINT_POS = (1, 1)

# Blank string used to erase the previous hint before writing a new one.
# 60 spaces is wider than any hint message.
HINT_CLEAR = " " * 60

