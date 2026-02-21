"""
Splash screen module for displaying the game logo on startup.
"""

import time
from pathlib import Path
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from asciimatics.screen import Screen


def get_logo_ascii_art() -> Optional[str]:
    """
    Load the logo ASCII art from the generated images directory.
    
    Returns the ASCII art string if available, None otherwise.
    """
    from cardio.assets import GENERATED_IMAGES_DIR, IMAGES_DIR, AsciiArtGenerator
    
    logo_txt = GENERATED_IMAGES_DIR / "logo.txt"
    logo_png = IMAGES_DIR / "logo.png"
    
    # Generate if not exists or source changed
    if logo_png.exists():
        generator = AsciiArtGenerator(output_dir=GENERATED_IMAGES_DIR, width=80)
        try:
            return generator.generate(str(logo_png), output_name="logo")
        except Exception:
            pass
    
    # Fall back to reading existing file
    if logo_txt.exists():
        return logo_txt.read_text()
    
    return None


def show_splash_screen(screen: "Screen", duration: float = 2.0) -> None:
    """
    Display the logo splash screen.
    
    Args:
        screen: The asciimatics screen to draw on.
        duration: How long to show the splash screen in seconds.
    """
    from .utils import dPos, show_text
    from .constants import Color
    
    logo_art = get_logo_ascii_art()
    
    if not logo_art:
        return
    
    screen.clear_buffer(0, 0, 0)
    
    lines = logo_art.split("\n")
    start_y = screen.height // 2 - len(lines) // 2
    
    for i, line in enumerate(lines):
        x = screen.width // 2 - len(line) // 2
        show_text(screen, dPos(x, start_y + i), line, color=Color.RED)
    
    # Add tagline below the logo
    tagline = "A roguelike deck-building card game"
    tagline_x = screen.width // 2 - len(tagline) // 2
    tagline_y = start_y + len(lines) + 2
    show_text(screen, dPos(tagline_x, tagline_y), tagline, color=Color.YELLOW)
    
    press_key_msg = "Press any key to continue..."
    msg_x = screen.width // 2 - len(press_key_msg) // 2
    msg_y = tagline_y + 2
    show_text(screen, dPos(msg_x, msg_y), press_key_msg, color=Color.GRAY)
    
    screen.refresh()
    
    # Wait for key or timeout
    start_time = time.time()
    while time.time() - start_time < duration:
        event = screen.get_event()
        if event is not None:
            break
        time.sleep(0.05)
