"""cardio.tui.menu — Main-menu TUI screen.

Presents three choices to the player before a run starts:

  1. **vs Computer** – the classic single-player mode.
  2. **vs LAN Multiplayer** – opens the lobby browser (see
     :class:`~cardio.tui.lobby_view.TUILobbyView`).
  3. **Exit** – quit the application cleanly from the main menu.

Navigation
----------
- ``↑`` / ``↓``  move the cursor between items.
- ``Enter``       confirms the highlighted item.

Return value
------------
``show()`` returns one of three string literals:

``"computer"``
    The player chose to fight the computer AI.

``"multiplayer"``
    The player chose LAN multiplayer.  By the time ``show()`` returns the lobby
    handshake is *not yet done* — the caller must subsequently open
    :class:`~cardio.tui.lobby_view.TUILobbyView` to complete the connection.

``"exit"``
    The player chose to quit.  The caller should call ``sys.exit(0)``.

Layout
------
The menu is drawn on the same :class:`~asciimatics.screen.Screen` instance that was
already opened by :class:`~cardio.tui.tuibase.TUIBaseMixin`.  The title is rendered
with the *doh* Figlet font (the same font used elsewhere in the game for short
messages) and the three menu items are displayed below it in a simple
cursor-highlighted list.
"""

from __future__ import annotations

from typing import Literal

from asciimatics.screen import Screen

from asciimatics.renderers import FigletText

from cardio.tui.tuibase import TUIBaseMixin
from cardio.tui.utils import dPos, show_text, get_keycode
from cardio.tui.constants import Color
from cardio.tui.menu_constants import ITEMS as _ITEMS, TOKENS as _TOKENS

# ── layout constants ───────────────────────────────────────────────────────────

_TITLE_FONT = "doh"
_TITLE_TEXT = "CARDIO"

# Vertical offset (in rows) from the screen centre to the top of the title block.
_TITLE_Y_OFFSET = -10

# Spacing between menu items (in rows).
_ITEM_SPACING = 2



class TUIMenu(TUIBaseMixin):
    """Full-screen main menu.

    Inherits :class:`~cardio.tui.tuibase.TUIBaseMixin` so it opens and owns a
    :class:`~asciimatics.screen.Screen`.  The caller should call :meth:`close` after
    :meth:`show` returns (or rely on the ``atexit`` handler registered by the mixin).

    Parameters
    ----------
    debug:
        Forwarded to :class:`~cardio.tui.tuibase.TUIBaseMixin`.
    """

    def __init__(self, debug: bool = False) -> None:
        super().__init__(debug=debug)

    # ── public API ─────────────────────────────────────────────────────────────

    def show(self) -> Literal["computer", "multiplayer", "exit"]:
        """Render the menu and block until the player confirms a choice.

        Returns ``"computer"``, ``"multiplayer"``, or ``"exit"``.
        """
        cursor = 0
        while True:
            self._redraw(cursor)
            keycode = get_keycode(self.screen)
            if keycode == Screen.KEY_UP:
                cursor = max(0, cursor - 1)
            elif keycode == Screen.KEY_DOWN:
                cursor = min(len(_ITEMS) - 1, cursor + 1)
            elif keycode in (Screen.KEY_RIGHT, 13):  # Enter / Return
                return _TOKENS[cursor]

    # ── rendering ──────────────────────────────────────────────────────────────

    def _redraw(self, cursor: int) -> None:
        """Clear the screen and draw the title + menu items."""
        self.screen.clear_buffer(0, 0, 0)

        cx = self.screen.width // 2
        cy = self.screen.height // 2

        # ── Title ─────────────────────────────────────────────────────────────
        title_renderer = FigletText(_TITLE_TEXT, _TITLE_FONT)
        title_lines = str(title_renderer).split("\n")
        title_w = max(len(line) for line in title_lines)
        title_h = len(title_lines)
        title_x = cx - title_w // 2
        title_y = cy + _TITLE_Y_OFFSET
        for i, line in enumerate(title_lines):
            show_text(
                self.screen,
                dPos(title_x, title_y + i),
                line,
                color=Color.CYAN,
            )

        # ── Subtitle / hint ────────────────────────────────────────────────────
        subtitle = "Use ↑ ↓ to navigate  •  Enter to confirm"
        show_text(
            self.screen,
            dPos(cx - len(subtitle) // 2, title_y + title_h + 1),
            subtitle,
            color=Color.GRAY,
        )

        # ── Menu items ─────────────────────────────────────────────────────────
        items_start_y = title_y + title_h + 3
        for i, label in enumerate(_ITEMS):
            y = items_start_y + i * _ITEM_SPACING
            if i == cursor:
                # Highlighted item: wrap in arrow decoration and use MAGENTA.
                # The Exit item uses RED to make its destructive nature obvious.
                display = f"▶  {label.strip()}  ◀"
                col = Color.RED if _TOKENS[i] == "exit" else Color.MAGENTA
            else:
                display = f"   {label.strip()}   "
                # Unhighlighted Exit is dimmed (GRAY) to de-emphasise it.
                col = Color.GRAY if _TOKENS[i] == "exit" else Color.WHITE
            x = cx - len(display) // 2
            show_text(self.screen, dPos(x, y), display, color=col)

        self.screen.refresh()

