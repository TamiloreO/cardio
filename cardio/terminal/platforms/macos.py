import os
import shutil
import sys
from typing import List, Optional

from ..launcher import TerminalLauncher
from ..config import TerminalConfig


class MacOSTerminalLauncher(TerminalLauncher):
    """Launcher for macOS Terminal.app and iTerm2."""

    def __init__(self, config: Optional[TerminalConfig] = None):
        super().__init__(config)
        self._terminal_type: Optional[str] = None

    def is_available(self) -> bool:
        if sys.platform != "darwin":
            return False
        
        # Check for iTerm2 first (better emoji support)
        if os.path.exists("/Applications/iTerm.app"):
            self._terminal_type = "iterm"
            return True
        
        # Fall back to Terminal.app
        if os.path.exists("/Applications/Utilities/Terminal.app"):
            self._terminal_type = "terminal"
            return True
        
        return False

    def get_terminal_name(self) -> str:
        if self._terminal_type == "iterm":
            return "iTerm2"
        return "Terminal.app"

    def build_launch_command(self, script_path: str, script_args: List[str]) -> List[str]:
        args_str = " ".join(f'"{arg}"' for arg in script_args) if script_args else ""
        python_cmd = f'"{sys.executable}" "{script_path}" {args_str}'.strip()

        if self._terminal_type == "iterm":
            return self._build_iterm_command(python_cmd)
        return self._build_terminal_app_command(python_cmd)

    def _build_iterm_command(self, python_cmd: str) -> List[str]:
        maximize_script = ""
        if self.config.dimensions.is_maximized():
            maximize_script = """
                tell application "System Events"
                    keystroke "f" using {control down, command down}
                end tell
            """
        
        applescript = f'''
            tell application "iTerm"
                activate
                set newWindow to (create window with default profile)
                tell current session of newWindow
                    write text "{python_cmd}"
                end tell
                {maximize_script}
            end tell
        '''
        return ["osascript", "-e", applescript]

    def _build_terminal_app_command(self, python_cmd: str) -> List[str]:
        maximize_script = ""
        if self.config.dimensions.is_maximized():
            maximize_script = """
                tell application "System Events"
                    keystroke "f" using {control down, command down}
                end tell
            """

        applescript = f'''
            tell application "Terminal"
                activate
                do script "{python_cmd}"
                {maximize_script}
            end tell
        '''
        return ["osascript", "-e", applescript]

    def supports_unicode(self) -> bool:
        return True

    def supports_maximized(self) -> bool:
        return True
