import os
import sys
from typing import Optional


class TerminalEnvironmentDetector:
    """Detects the current terminal environment and its capabilities."""

    LAUNCHED_ENV_VAR = "CARDIO_LAUNCHED_TERMINAL"

    @classmethod
    def is_launched_by_cardio(cls) -> bool:
        """Check if the current process was launched by Cardio's terminal launcher."""
        return os.environ.get(cls.LAUNCHED_ENV_VAR) == "1"

    @classmethod
    def mark_as_launched(cls) -> None:
        """Set environment variable to indicate Cardio launched this terminal."""
        os.environ[cls.LAUNCHED_ENV_VAR] = "1"

    @classmethod
    def is_interactive_terminal(cls) -> bool:
        """Check if we're running in an interactive terminal."""
        return sys.stdin.isatty() and sys.stdout.isatty()

    @classmethod
    def get_terminal_size(cls) -> tuple:
        """Get the current terminal size (columns, lines)."""
        try:
            size = os.get_terminal_size()
            return (size.columns, size.lines)
        except OSError:
            return (80, 24)  # Default fallback

    @classmethod
    def meets_minimum_size(cls, min_width: int = 160, min_height: int = 52) -> bool:
        """Check if terminal meets minimum size requirements."""
        width, height = cls.get_terminal_size()
        return width >= min_width and height >= min_height

    @classmethod
    def detect_terminal_type(cls) -> Optional[str]:
        """Attempt to detect the terminal emulator type."""
        # Check common environment variables
        term_program = os.environ.get("TERM_PROGRAM", "")
        wt_session = os.environ.get("WT_SESSION", "")
        
        if wt_session:
            return "windows_terminal"
        if term_program == "Apple_Terminal":
            return "terminal_app"
        if term_program == "iTerm.app":
            return "iterm"
        if "KITTY_WINDOW_ID" in os.environ:
            return "kitty"
        if "ALACRITTY_LOG" in os.environ or "ALACRITTY_SOCKET" in os.environ:
            return "alacritty"
        if os.environ.get("COLORTERM") == "gnome-terminal":
            return "gnome_terminal"
        if "KONSOLE_VERSION" in os.environ:
            return "konsole"
        
        return os.environ.get("TERM", None)

    @classmethod
    def is_windows_terminal(cls) -> bool:
        """Check if running inside Windows Terminal."""
        return bool(os.environ.get("WT_SESSION"))

    @classmethod
    def is_cmd_exe(cls) -> bool:
        """Check if running inside cmd.exe (not Windows Terminal)."""
        if sys.platform != "win32":
            return False
        return not cls.is_windows_terminal() and os.environ.get("PROMPT") is not None
