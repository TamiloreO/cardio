"""Tests for the splash screen module."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch
from PIL import Image

from cardio.tui.splash import get_logo_ascii_art


class TestGetLogoAsciiArt:
    """Test suite for get_logo_ascii_art function."""

    def test_returns_none_when_no_logo(self, tmp_path):
        """Test returns None when logo files don't exist."""
        empty_images = tmp_path / "images"
        empty_generated = tmp_path / "generated"
        empty_images.mkdir()
        empty_generated.mkdir()

        with patch("cardio.assets.IMAGES_DIR", empty_images):
            with patch("cardio.assets.GENERATED_IMAGES_DIR", empty_generated):
                result = get_logo_ascii_art()

        assert result is None

    def test_generates_logo_when_png_exists(self, tmp_path):
        """Test that logo is generated when PNG exists."""
        images_dir = tmp_path / "images"
        generated_dir = tmp_path / "generated"
        images_dir.mkdir()
        generated_dir.mkdir()

        # Create a simple logo image
        logo_path = images_dir / "logo.png"
        img = Image.new("L", (20, 10), color=128)
        img.save(logo_path)

        with patch("cardio.assets.IMAGES_DIR", images_dir):
            with patch("cardio.assets.GENERATED_IMAGES_DIR", generated_dir):
                result = get_logo_ascii_art()

        assert result is not None
        assert isinstance(result, str)
        assert (generated_dir / "logo.txt").exists()

    def test_reads_existing_generated_file(self, tmp_path):
        """Test that existing generated file is read."""
        images_dir = tmp_path / "images"
        generated_dir = tmp_path / "generated"
        images_dir.mkdir()
        generated_dir.mkdir()

        # Create logo image
        logo_path = images_dir / "logo.png"
        img = Image.new("L", (20, 10), color=128)
        img.save(logo_path)

        # Pre-generate the ASCII art
        from cardio.assets import AsciiArtGenerator
        generator = AsciiArtGenerator(output_dir=generated_dir, width=80)
        expected = generator.generate(str(logo_path), output_name="logo")

        with patch("cardio.assets.IMAGES_DIR", images_dir):
            with patch("cardio.assets.GENERATED_IMAGES_DIR", generated_dir):
                result = get_logo_ascii_art()

        assert result == expected

    def test_falls_back_to_txt_when_png_missing(self, tmp_path):
        """Test fallback to .txt file when PNG doesn't exist."""
        images_dir = tmp_path / "images"
        generated_dir = tmp_path / "generated"
        images_dir.mkdir()
        generated_dir.mkdir()

        # Only create the txt file, no PNG
        expected_art = "FALLBACK\nASCII\nART"
        (generated_dir / "logo.txt").write_text(expected_art)

        with patch("cardio.assets.IMAGES_DIR", images_dir):
            with patch("cardio.assets.GENERATED_IMAGES_DIR", generated_dir):
                result = get_logo_ascii_art()

        assert result == expected_art


try:
    import asciimatics
    HAS_ASCIIMATICS = True
except ImportError:
    HAS_ASCIIMATICS = False


@pytest.mark.skipif(not HAS_ASCIIMATICS, reason="asciimatics not installed")
class TestShowSplashScreen:
    """Test suite for show_splash_screen function.

    Note: These tests require asciimatics to be installed.
    """

    def test_handles_missing_logo(self):
        """Test that missing logo is handled gracefully."""
        from cardio.tui.splash import show_splash_screen

        mock_screen = Mock()

        with patch("cardio.tui.splash.get_logo_ascii_art") as mock_get_logo:
            mock_get_logo.return_value = None

            # Should not raise
            show_splash_screen(mock_screen)

        # Screen should not be modified if no logo
        mock_screen.clear_buffer.assert_not_called()

    def test_shows_logo_on_screen(self):
        """Test that logo is displayed on screen."""
        from cardio.tui.splash import show_splash_screen

        mock_screen = Mock()
        mock_screen.height = 100
        mock_screen.width = 160
        mock_screen.get_event.return_value = Mock()  # Simulate key press

        with patch("cardio.tui.splash.get_logo_ascii_art") as mock_get_logo:
            mock_get_logo.return_value = "TEST\nLOGO"

            show_splash_screen(mock_screen, duration=0.1)

        mock_screen.clear_buffer.assert_called()
        mock_screen.refresh.assert_called()

    def test_exits_early_on_keypress(self):
        """Test that splash exits early on key press."""
        from cardio.tui.splash import show_splash_screen
        import time

        mock_screen = Mock()
        mock_screen.height = 100
        mock_screen.width = 160
        mock_screen.get_event.return_value = Mock()  # Immediate key press

        with patch("cardio.tui.splash.get_logo_ascii_art") as mock_get_logo:
            mock_get_logo.return_value = "TEST"

            start = time.time()
            show_splash_screen(mock_screen, duration=5.0)
            elapsed = time.time() - start

        # Should exit much faster than duration due to key press
        assert elapsed < 1.0
