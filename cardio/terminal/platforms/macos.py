import os
import shutil
import subprocess
import sys
from typing import Dict, List, Optional

from ..launcher import TerminalLauncher
from ..config import TerminalConfig


class MacOSTerminalLauncher(TerminalLauncher):
    """Launcher for macOS Terminal.app and iTerm2.
    
    Uses AppleScript to launch terminals. Environment variables are passed
    by exporting them explicitly in the shell command since AppleScript
    launches a new shell session.
    """

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

    def build_launch_command(
        self, script_path: str, script_args: List[str], env_exports: str = ""
    ) -> List[str]:
        """Build AppleScript command to launch terminal.
        
        Args:
            script_path: Path to the script to run.
            script_args: Arguments for the script.
            env_exports: Shell export statements for environment variables.
        """
        args_str = " ".join(f'"{arg}"' for arg in script_args) if script_args else ""
        python_cmd = f'"{sys.executable}" "{script_path}" {args_str}'.strip()
        
        if env_exports:
            full_cmd = f'{env_exports} && {python_cmd}'
        else:
            full_cmd = python_cmd

        if self._terminal_type == "iterm":
            return self._build_iterm_command(full_cmd)
        return self._build_terminal_app_command(full_cmd)

    def _build_env_exports(self, env: Dict[str, str]) -> str:
        """Build shell export statements for environment variables."""
        exports = []
        for key, value in env.items():
            escaped_value = value.replace("'", "'\\''")
            exports.append(f"export {key}='{escaped_value}'")
        return " && ".join(exports)

    def launch(
        self,
        script_path: str,
        script_args: Optional[List[str]] = None,
        env: Optional[Dict[str, str]] = None,
    ) -> subprocess.Popen:
        """Launch the script in macOS terminal with environment variables.
        
        Environment variables are exported explicitly in the shell command
        since AppleScript creates a new shell session.
        """
        args = script_args or []
        effective_env = env if env is not None else os.environ.copy()
        
        env_exports = self._build_env_exports(effective_env)
        command = self.build_launch_command(script_path, args, env_exports)
        
        return subprocess.Popen(command)

    def _build_iterm_command(self, full_cmd: str) -> List[str]:
        maximize_script = ""
        if self.config.dimensions.is_maximized():
            maximize_script = """
                tell application "System Events"
                    keystroke "f" using {control down, command down}
                end tell
            """
        
        escaped_cmd = full_cmd.replace('"', '\\"')
        applescript = f'''
            tell application "iTerm"
                activate
                set newWindow to (create window with default profile)
                tell current session of newWindow
                    write text "{escaped_cmd}"
                end tell
                {maximize_script}
            end tell
        '''
        return ["osascript", "-e", applescript]

    def _build_terminal_app_command(self, full_cmd: str) -> List[str]:
        maximize_script = ""
        if self.config.dimensions.is_maximized():
            maximize_script = """
                tell application "System Events"
                    keystroke "f" using {control down, command down}
                end tell
            """

        escaped_cmd = full_cmd.replace('"', '\\"')
        applescript = f'''
            tell application "Terminal"
                activate
                do script "{escaped_cmd}"
                {maximize_script}
            end tell
        '''
        return ["osascript", "-e", applescript]

    def supports_unicode(self) -> bool:
        return True

    def supports_maximized(self) -> bool:
        return True
