"""Tests for the splash screen module."""

import sys
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Mock asciimatics before importing splash module
sys.modules['asciimatics'] = MagicMock()
sys.modules['asciimatics.screen'] = MagicMock()
sys.modules['asciimatics.constants'] = MagicMock()
sys.modules['asciimatics.effects'] = MagicMock()
sys.modules['asciimatics.renderers'] = MagicMock()
sys.modules['asciimatics.event'] = MagicMock()

from cardio.tui.splash import (
    get_logo_path,
    load_logo,
    show_splash_screen,
    LOGO_FILENAME,
)
from cardio.tui.constants import Color


class TestGetLogoPath:
    """Test suite for get_logo_path function."""

    def test_returns_path_object(self):
        """Test that get_logo_path returns a Path object."""
        result = get_logo_path()
        assert isinstance(result, Path)

    def test_path_ends_with_logo_filename(self):
        """Test that path ends with the logo filename."""
        result = get_logo_path()
        assert result.name == LOGO_FILENAME

    def test_path_includes_generatedimages(self):
        """Test that path includes generatedimages directory."""
        result = get_logo_path()
        assert "generatedimages" in result.parts


class TestLoadLogo:
    """Test suite for load_logo function."""

    def test_returns_none_when_file_missing(self, tmp_path, monkeypatch):
        """Test that load_logo returns None when logo file doesn't exist."""
        monkeypatch.setattr(
            "cardio.tui.splash.get_logo_path",
            lambda: tmp_path / "nonexistent.txt"
        )
        result = load_logo()
        assert result is None

    def test_returns_content_when_file_exists(self, tmp_path, monkeypatch):
        """Test that load_logo returns file content when logo exists."""
        logo_file = tmp_path / "logo.txt"
        logo_content = "ASCII ART LOGO"
        logo_file.write_text(logo_content)

        monkeypatch.setattr(
            "cardio.tui.splash.get_logo_path",
            lambda: logo_file
        )

        result = load_logo()
        assert result == logo_content


class TestShowSplashScreen:
    """Test suite for show_splash_screen function."""

    def test_does_nothing_when_logo_missing(self, monkeypatch):
        """Test that show_splash_screen exits early when no logo."""
        monkeypatch.setattr("cardio.tui.splash.load_logo", lambda: None)

        mock_screen = Mock()
        show_splash_screen(mock_screen)

        mock_screen.clear_buffer.assert_not_called()

    def test_clears_screen_buffer(self, tmp_path, monkeypatch):
        """Test that screen buffer is cleared."""
        monkeypatch.setattr("cardio.tui.splash.load_logo", lambda: "LOGO")
        monkeypatch.setattr("cardio.tui.splash.wait_for_any_key", lambda s: None)

        mock_screen = Mock()
        mock_screen.height = 50
        mock_screen.width = 80

        show_splash_screen(mock_screen)

        mock_screen.clear_buffer.assert_called_once_with(0, 0, 0)

    def test_refreshes_screen(self, tmp_path, monkeypatch):
        """Test that screen is refreshed after drawing."""
        monkeypatch.setattr("cardio.tui.splash.load_logo", lambda: "LOGO")
        monkeypatch.setattr("cardio.tui.splash.wait_for_any_key", lambda s: None)

        mock_screen = Mock()
        mock_screen.height = 50
        mock_screen.width = 80

        show_splash_screen(mock_screen)

        mock_screen.refresh.assert_called_once()

    def test_waits_for_key_by_default(self, tmp_path, monkeypatch):
        """Test that splash waits for key by default."""
        monkeypatch.setattr("cardio.tui.splash.load_logo", lambda: "LOGO")

        wait_called = []

        def mock_wait(screen):
            wait_called.append(True)

        monkeypatch.setattr("cardio.tui.splash.wait_for_any_key", mock_wait)

        mock_screen = Mock()
        mock_screen.height = 50
        mock_screen.width = 80

        show_splash_screen(mock_screen, wait_for_key=True)

        assert len(wait_called) == 1

    def test_respects_duration_parameter(self, tmp_path, monkeypatch):
        """Test that duration parameter uses sleep instead of wait."""
        monkeypatch.setattr("cardio.tui.splash.load_logo", lambda: "LOGO")

        sleep_durations = []

        def mock_sleep(duration):
            sleep_durations.append(duration)

        monkeypatch.setattr("time.sleep", mock_sleep)

        wait_called = []

        def mock_wait(screen):
            wait_called.append(True)

        monkeypatch.setattr("cardio.tui.splash.wait_for_any_key", mock_wait)

        mock_screen = Mock()
        mock_screen.height = 50
        mock_screen.width = 80

        show_splash_screen(mock_screen, duration=2.0, wait_for_key=True)

        assert 2.0 in sleep_durations
        assert len(wait_called) == 0

    def test_centers_logo_vertically(self, tmp_path, monkeypatch):
        """Test that logo is centered vertically on screen."""
        logo_lines = ["LINE1", "LINE2", "LINE3"]
        monkeypatch.setattr("cardio.tui.splash.load_logo", lambda: "\n".join(logo_lines))
        monkeypatch.setattr("cardio.tui.splash.wait_for_any_key", lambda s: None)

        show_text_calls = []

        def mock_show_text(screen, pos, text, color=None):
            show_text_calls.append((pos, text))

        monkeypatch.setattr("cardio.tui.splash.show_text", mock_show_text)

        mock_screen = Mock()
        mock_screen.height = 50
        mock_screen.width = 80

        show_splash_screen(mock_screen)

        expected_start_y = (50 - 3) // 2
        assert show_text_calls[0][0].y == expected_start_y

    def test_centers_logo_horizontally(self, tmp_path, monkeypatch):
        """Test that logo is centered horizontally on screen."""
        logo_text = "LOGO_TEXT"
        monkeypatch.setattr("cardio.tui.splash.load_logo", lambda: logo_text)
        monkeypatch.setattr("cardio.tui.splash.wait_for_any_key", lambda s: None)

        show_text_calls = []

        def mock_show_text(screen, pos, text, color=None):
            show_text_calls.append((pos, text))

        monkeypatch.setattr("cardio.tui.splash.show_text", mock_show_text)

        mock_screen = Mock()
        mock_screen.height = 50
        mock_screen.width = 80

        show_splash_screen(mock_screen)

        expected_start_x = (80 - len(logo_text)) // 2
        assert show_text_calls[0][0].x == expected_start_x

    def test_uses_specified_color(self, tmp_path, monkeypatch):
        """Test that specified color is used for rendering."""
        monkeypatch.setattr("cardio.tui.splash.load_logo", lambda: "LOGO")
        monkeypatch.setattr("cardio.tui.splash.wait_for_any_key", lambda s: None)

        show_text_calls = []

        def mock_show_text(screen, pos, text, color=None):
            show_text_calls.append((pos, text, color))

        monkeypatch.setattr("cardio.tui.splash.show_text", mock_show_text)

        mock_screen = Mock()
        mock_screen.height = 50
        mock_screen.width = 80

        show_splash_screen(mock_screen, color=Color.YELLOW)

        assert show_text_calls[0][2] == Color.YELLOW

    def test_default_color_is_cyan(self, tmp_path, monkeypatch):
        """Test that default color is cyan."""
        monkeypatch.setattr("cardio.tui.splash.load_logo", lambda: "LOGO")
        monkeypatch.setattr("cardio.tui.splash.wait_for_any_key", lambda s: None)

        show_text_calls = []

        def mock_show_text(screen, pos, text, color=None):
            show_text_calls.append((pos, text, color))

        monkeypatch.setattr("cardio.tui.splash.show_text", mock_show_text)

        mock_screen = Mock()
        mock_screen.height = 50
        mock_screen.width = 80

        show_splash_screen(mock_screen)

        assert show_text_calls[0][2] == Color.CYAN
