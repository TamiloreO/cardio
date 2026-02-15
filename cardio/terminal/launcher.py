from abc import ABC, abstractmethod
from typing import Dict, List, Optional
import os
import subprocess
import sys

from .config import TerminalConfig


class TerminalLauncher(ABC):
    """Abstract interface for platform-specific terminal launchers.
    
    Subclasses implement platform-specific logic for launching scripts
    in external terminal windows with proper configuration (maximized,
    unicode support, etc.).
    """

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

    def launch(
        self,
        script_path: str,
        script_args: Optional[List[str]] = None,
        env: Optional[Dict[str, str]] = None,
    ) -> subprocess.Popen:
        """Launch the script in this terminal.
        
        Args:
            script_path: Path to the Python script to execute.
            script_args: Command-line arguments to pass to the script.
            env: Environment variables for the child process. If None,
                 inherits from current process via os.environ.copy().
        
        Returns:
            The Popen object for the launched process.
        """
        args = script_args or []
        command = self.build_launch_command(script_path, args)
        effective_env = env if env is not None else os.environ.copy()
        return subprocess.Popen(command, env=effective_env)

    def supports_unicode(self) -> bool:
        """Check if this terminal supports unicode/emoji rendering."""
        return True

    def supports_maximized(self) -> bool:
        """Check if this terminal supports launching maximized."""
        return True
