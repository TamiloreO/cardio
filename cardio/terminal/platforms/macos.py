import os
import subprocess
import sys
from typing import Dict, List, Optional

from ..launcher import TerminalLauncher
from ..config import TerminalConfig


class MacOSTerminalLauncher(TerminalLauncher):
    """Launcher for macOS Terminal.app and iTerm2.
    
    Uses AppleScript to launch terminal applications. Environment variables
    are exported in the shell command to ensure they are available in the
    new terminal session.
    """

    def __init__(self, config: Optional[TerminalConfig] = None):
        super().__init__(config)
        self._terminal_type: Optional[str] = None

    def is_available(self) -> bool:
        if sys.platform != "darwin":
            return False
        
        if os.path.exists("/Applications/iTerm.app"):
            self._terminal_type = "iterm"
            return True
        
        if os.path.exists("/Applications/Utilities/Terminal.app"):
            self._terminal_type = "terminal"
            return True
        
        return False

    def get_terminal_name(self) -> str:
        if self._terminal_type == "iterm":
            return "iTerm2"
        return "Terminal.app"

    def _build_env_exports(self, env: Dict[str, str]) -> str:
        """Build shell export statements for environment variables."""
        from ..detection import TerminalEnvironmentDetector
        marker_var = TerminalEnvironmentDetector.LAUNCHED_ENV_VAR
        if marker_var in env:
            return f'export {marker_var}="{env[marker_var]}"; '
        return ""

    def build_launch_command(
        self, script_path: str, script_args: List[str], env_exports: str = ""
    ) -> List[str]:
        args_str = " ".join(f'"{arg}"' for arg in script_args) if script_args else ""
        python_cmd = f'{env_exports}"{sys.executable}" "{script_path}" {args_str}'.strip()

        if self._terminal_type == "iterm":
            return self._build_iterm_command(python_cmd)
        return self._build_terminal_app_command(python_cmd)

    def launch(
        self,
        script_path: str,
        script_args: Optional[List[str]] = None,
        env: Optional[Dict[str, str]] = None,
    ) -> subprocess.Popen:
        """Launch the script in a macOS terminal.
        
        Environment variables are passed by embedding export statements
        in the shell command, since AppleScript launches a new shell session.
        """
        args = script_args or []
        effective_env = env if env is not None else os.environ.copy()
        env_exports = self._build_env_exports(effective_env)
        command = self.build_launch_command(script_path, args, env_exports)
        return subprocess.Popen(command, env=effective_env)

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
