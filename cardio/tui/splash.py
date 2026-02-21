"""
Splash screen module for displaying the game logo on startup.
"""

import sys
import time
from pathlib import Path
from typing import Optional

# Mock asciimatics imports for type checking without requiring it at module level
from asciimatics.screen import Screen

from .utils import dPos, show_text, wait_for_any_key
from .constants import Color

LOGO_FILENAME = "logo.txt"


def get_logo_path() -> Path:
    """
    Get the path to the generated logo ASCII art file.

    Returns:
        Path to the logo.txt file in the generatedimages directory.
    """
    from cardio.assets import GENERATED_IMAGES_DIR
    return GENERATED_IMAGES_DIR / LOGO_FILENAME


def load_logo() -> Optional[str]:
    """
    Load the logo ASCII art from the generated images directory.

    Returns:
        The logo ASCII art string if the file exists, None otherwise.
    """
    logo_path = get_logo_path()
    if not logo_path.exists():
        return None
    return logo_path.read_text()


def show_splash_screen(
    screen: Screen,
    duration: Optional[float] = None,
    wait_for_key: bool = True,
    color: Color = Color.CYAN,
) -> None:
    """
    Display the logo splash screen.

    Args:
        screen: The asciimatics screen to draw on.
        duration: How long to show the splash screen in seconds. If None and
                  wait_for_key is True, waits for a key press.
        wait_for_key: Whether to wait for a key press (default True).
        color: The color to use for rendering the logo (default CYAN).
    """
    logo = load_logo()

    if not logo:
        return

    screen.clear_buffer(0, 0, 0)

    lines = logo.split("\n")
    logo_height = len(lines)
    logo_width = max(len(line) for line in lines) if lines else 0

    start_y = max(0, (screen.height - logo_height) // 2)
    start_x = max(0, (screen.width - logo_width) // 2)

    for i, line in enumerate(lines):
        show_text(screen, dPos(start_x, start_y + i), line, color=color)

    screen.refresh()

    if duration is not None:
        time.sleep(duration)
    elif wait_for_key:
        wait_for_any_key(screen)
