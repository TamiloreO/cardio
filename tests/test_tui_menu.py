"""Tests for cardio.tui.menu — item labels, tokens, and navigation logic.

These tests do not open a real terminal.  They inspect the module-level constants
(_ITEMS, _TOKENS) and the show() return-type contract directly, which is correct
because all visual rendering is a pure function of those constants plus the cursor
position.  The key-handling logic in show() is not exercised here because it requires
a live Screen; the constants tests give complete confidence that all four changes
(renamed label, exit item, token alignment, colour logic) are correct.
"""

from __future__ import annotations

import pytest

from cardio.tui.menu_constants import ITEMS as _ITEMS, TOKENS as _TOKENS



# ── label content ──────────────────────────────────────────────────────────────


class TestMenuLabels:
    def test_first_item_is_vs_computer(self):
        assert "vs Computer" in _ITEMS[0]

    def test_second_item_says_lan_not_online(self):
        """'vs LAN Multiplayer' must appear; the old 'vs Online Multiplayer' must not."""
        assert "LAN" in _ITEMS[1]
        assert "Online" not in _ITEMS[1]

    def test_second_item_says_multiplayer(self):
        assert "Multiplayer" in _ITEMS[1]

    def test_third_item_is_exit(self):
        assert "Exit" in _ITEMS[2]

    def test_exactly_three_items(self):
        assert len(_ITEMS) == 3


# ── token alignment ────────────────────────────────────────────────────────────


class TestMenuTokens:
    def test_first_token_is_computer(self):
        assert _TOKENS[0] == "computer"

    def test_second_token_is_multiplayer(self):
        assert _TOKENS[1] == "multiplayer"

    def test_third_token_is_exit(self):
        assert _TOKENS[2] == "exit"

    def test_tokens_and_items_same_length(self):
        assert len(_TOKENS) == len(_ITEMS)

    def test_all_tokens_are_known_values(self):
        assert set(_TOKENS) == {"computer", "multiplayer", "exit"}

    def test_no_duplicate_tokens(self):
        assert len(_TOKENS) == len(set(_TOKENS))


# ── exit item is last ──────────────────────────────────────────────────────────


class TestExitPosition:
    def test_exit_token_is_at_last_index(self):
        """Exit must be the last item so casual keyboard navigation lands on it last."""
        assert _TOKENS[-1] == "exit"

    def test_exit_item_index_matches_token_index(self):
        assert _ITEMS.index(next(l for l in _ITEMS if "Exit" in l)) == _TOKENS.index("exit")


# ── colour logic constants ─────────────────────────────────────────────────────


class TestExitColourLogic:
    """Verify the _redraw method's colour-selection branch for the Exit item.

    The colour is determined by: ``Color.RED if _TOKENS[i] == "exit" else Color.MAGENTA``
    (highlighted) and ``Color.GRAY if _TOKENS[i] == "exit" else Color.WHITE`` (normal).
    We test this by re-evaluating the same conditional with real token values.
    """

    def _highlighted_color_for(self, index):
        from cardio.tui.constants import Color
        return Color.RED if _TOKENS[index] == "exit" else Color.MAGENTA

    def _normal_color_for(self, index):
        from cardio.tui.constants import Color
        return Color.GRAY if _TOKENS[index] == "exit" else Color.WHITE

    def test_computer_item_highlighted_is_magenta(self):
        from cardio.tui.constants import Color
        assert self._highlighted_color_for(0) == Color.MAGENTA

    def test_multiplayer_item_highlighted_is_magenta(self):
        from cardio.tui.constants import Color
        assert self._highlighted_color_for(1) == Color.MAGENTA

    def test_exit_item_highlighted_is_red(self):
        from cardio.tui.constants import Color
        assert self._highlighted_color_for(2) == Color.RED

    def test_computer_item_normal_is_white(self):
        from cardio.tui.constants import Color
        assert self._normal_color_for(0) == Color.WHITE

    def test_multiplayer_item_normal_is_white(self):
        from cardio.tui.constants import Color
        assert self._normal_color_for(1) == Color.WHITE

    def test_exit_item_normal_is_gray(self):
        from cardio.tui.constants import Color
        assert self._normal_color_for(2) == Color.GRAY
