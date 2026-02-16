"""Reusable dialog components for the TUI."""

from asciimatics.screen import Screen
from .utils import show_text, dPos, get_keycode
from .constants import Color


def show_confirmation_dialog(screen: Screen, message: str, default_yes: bool = False) -> bool:
    """Show a Y/N confirmation dialog. Returns True if confirmed, False otherwise."""
    cursor = 0 if default_yes else 1
    options = ["Yes", "No"]

    while True:
        # Draw dialog box area
        box_width = max(len(message) + 8, 30)
        box_height = 7
        box_x = (screen.width - box_width) // 2
        box_y = (screen.height - box_height) // 2

        # Clear area and draw border
        for y in range(box_height):
            screen.print_at(" " * box_width, box_x, box_y + y)

        # Draw border
        screen.print_at("┌" + "─" * (box_width - 2) + "┐", box_x, box_y)
        for y in range(1, box_height - 1):
            screen.print_at("│", box_x, box_y + y)
            screen.print_at("│", box_x + box_width - 1, box_y + y)
        screen.print_at("└" + "─" * (box_width - 2) + "┘", box_x, box_y + box_height - 1)

        # Draw message
        msg_x = (screen.width - len(message)) // 2
        show_text(screen, dPos(msg_x, box_y + 2), message, Color.WHITE)

        # Draw options
        options_y = box_y + 4
        for i, opt in enumerate(options):
            if i == cursor:
                text = f"> {opt} <"
                color = Color.YELLOW
            else:
                text = f"  {opt}  "
                color = Color.WHITE
            opt_x = box_x + (box_width // 4) * (i * 2 + 1) - len(text) // 2
            show_text(screen, dPos(opt_x, options_y), text, color)

        screen.refresh()

        keycode = get_keycode(screen)
        if keycode == Screen.KEY_LEFT or keycode == Screen.KEY_RIGHT:
            cursor = 1 - cursor
        elif keycode == 13:  # Enter
            return cursor == 0
        elif keycode == ord('y') or keycode == ord('Y'):
            return True
        elif keycode == ord('n') or keycode == ord('N') or keycode == 27:  # N or Escape
            return False
