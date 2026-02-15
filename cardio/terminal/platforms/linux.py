import os
import shutil
import subprocess
import sys
from typing import Dict, List, Optional, Tuple

from ..launcher import TerminalLauncher
from ..config import TerminalConfig


class LinuxTerminalLauncher(TerminalLauncher):
    """Launcher for Linux terminal emulators.
    
    Supports multiple terminal emulators in order of preference for
    Unicode/emoji support. Environment variables are passed explicitly
    to subprocess.Popen to ensure reliable inheritance.
    """

    TERMINAL_PREFERENCES: List[Tuple[str, str]] = [
        ("kitty", "Kitty"),
        ("alacritty", "Alacritty"),
        ("gnome-terminal", "GNOME Terminal"),
        ("konsole", "Konsole"),
        ("xfce4-terminal", "XFCE Terminal"),
        ("mate-terminal", "MATE Terminal"),
        ("tilix", "Tilix"),
        ("terminator", "Terminator"),
        ("xterm", "XTerm"),
    ]

    def __init__(self, config: Optional[TerminalConfig] = None):
        super().__init__(config)
        self._terminal_executable: Optional[str] = None
        self._terminal_name: Optional[str] = None

    def is_available(self) -> bool:
        if sys.platform not in ("linux", "linux2"):
            return False
        
        for executable, name in self.TERMINAL_PREFERENCES:
            if shutil.which(executable):
                self._terminal_executable = executable
                self._terminal_name = name
                return True
        
        return False

    def get_terminal_name(self) -> str:
        return self._terminal_name or "Unknown Terminal"

    def build_launch_command(self, script_path: str, script_args: List[str]) -> List[str]:
        if not self._terminal_executable:
            raise RuntimeError("No terminal emulator found")

        builder = TerminalCommandBuilder(
            self._terminal_executable,
            self.config,
            script_path,
            script_args,
        )
        return builder.build()

    def launch(
        self,
        script_path: str,
        script_args: Optional[List[str]] = None,
        env: Optional[Dict[str, str]] = None,
    ) -> subprocess.Popen:
        """Launch the script in a Linux terminal emulator.
        
        Environment variables are passed explicitly via the env parameter
        to ensure they are inherited by the child process.
        """
        args = script_args or []
        command = self.build_launch_command(script_path, args)
        effective_env = env if env is not None else os.environ.copy()
        return subprocess.Popen(command, env=effective_env)

    def supports_unicode(self) -> bool:
        return self._terminal_executable not in ("xterm",)

    def supports_maximized(self) -> bool:
        return self._terminal_executable in (
            "gnome-terminal", "konsole", "xfce4-terminal", 
            "mate-terminal", "tilix", "terminator"
        )


class TerminalCommandBuilder:
    """Builds terminal-specific command line arguments."""

    def __init__(
        self,
        terminal: str,
        config: TerminalConfig,
        script_path: str,
        script_args: List[str],
    ):
        self.terminal = terminal
        self.config = config
        self.script_path = script_path
        self.script_args = script_args

    def build(self) -> List[str]:
        method_name = f"_build_{self.terminal.replace('-', '_')}"
        builder_method = getattr(self, method_name, self._build_generic)
        return builder_method()

    def _get_script_command(self) -> str:
        args_str = " ".join(self.script_args)
        return f"{sys.executable} {self.script_path} {args_str}".strip()

    def _build_gnome_terminal(self) -> List[str]:
        cmd = ["gnome-terminal"]
        if self.config.dimensions.is_maximized():
            cmd.append("--maximize")
        if self.config.title:
            cmd.extend(["--title", self.config.title])
        cmd.extend(["--", sys.executable, self.script_path] + self.script_args)
        return cmd

    def _build_konsole(self) -> List[str]:
        cmd = ["konsole"]
        if self.config.dimensions.is_maximized():
            cmd.append("--fullscreen")
        if self.config.title:
            cmd.extend(["--title", self.config.title])
        cmd.extend(["-e", sys.executable, self.script_path] + self.script_args)
        return cmd

    def _build_xfce4_terminal(self) -> List[str]:
        cmd = ["xfce4-terminal"]
        if self.config.dimensions.is_maximized():
            cmd.append("--maximize")
        if self.config.title:
            cmd.extend(["--title", self.config.title])
        cmd.extend(["-e", self._get_script_command()])
        return cmd

    def _build_mate_terminal(self) -> List[str]:
        cmd = ["mate-terminal"]
        if self.config.dimensions.is_maximized():
            cmd.append("--maximize")
        if self.config.title:
            cmd.extend(["--title", self.config.title])
        cmd.extend(["-e", self._get_script_command()])
        return cmd

    def _build_tilix(self) -> List[str]:
        cmd = ["tilix"]
        if self.config.dimensions.is_maximized():
            cmd.append("--maximize")
        if self.config.title:
            cmd.extend(["--title", self.config.title])
        cmd.extend(["-e", self._get_script_command()])
        return cmd

    def _build_terminator(self) -> List[str]:
        cmd = ["terminator"]
        if self.config.dimensions.is_maximized():
            cmd.append("--maximise")
        if self.config.title:
            cmd.extend(["--title", self.config.title])
        cmd.extend(["-e", self._get_script_command()])
        return cmd

    def _build_kitty(self) -> List[str]:
        cmd = ["kitty"]
        if self.config.title:
            cmd.extend(["--title", self.config.title])
        cmd.extend([sys.executable, self.script_path] + self.script_args)
        return cmd

    def _build_alacritty(self) -> List[str]:
        cmd = ["alacritty"]
        if self.config.title:
            cmd.extend(["--title", self.config.title])
        cmd.extend(["-e", sys.executable, self.script_path] + self.script_args)
        return cmd

    def _build_xterm(self) -> List[str]:
        cmd = ["xterm"]
        if self.config.title:
            cmd.extend(["-title", self.config.title])
        cmd.extend(["-e", sys.executable, self.script_path] + self.script_args)
        return cmd

    def _build_generic(self) -> List[str]:
        return [self.terminal, "-e", self._get_script_command()]
