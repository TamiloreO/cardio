from abc import ABC, abstractmethod
from typing import List, Optional
import subprocess
import sys

from .config import TerminalConfig


class TerminalLauncher(ABC):
    """Abstract interface for platform-specific terminal launchers."""

    def __init__(self, config: Optional[TerminalConfig] = None):
        self.config = config or TerminalConfig.default()

    @abstractmethod
    def is_available(self) -> bool:
        """Check if this terminal is available on the system."""
        pass

    @abstractmethod
    def build_launch_command(self, script_path: str, script_args: List[str]) -> List[str]:
        """Build the command to launch the script in this terminal."""
        pass

    @abstractmethod
    def get_terminal_name(self) -> str:
        """Return the human-readable name of this terminal."""
        pass

    def launch(self, script_path: str, script_args: Optional[List[str]] = None) -> subprocess.Popen:
        """Launch the script in this terminal."""
        args = script_args or []
        command = self.build_launch_command(script_path, args)
        return subprocess.Popen(command)

    def supports_unicode(self) -> bool:
        """Check if this terminal supports unicode/emoji rendering."""
        return True

    def supports_maximized(self) -> bool:
        """Check if this terminal supports launching maximized."""
        return True
