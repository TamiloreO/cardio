"""Terminal launcher module for opening external terminal windows with maximum size."""

import os
import sys
import shutil
import subprocess
import platform
from typing import Optional, Tuple, List


class TerminalLauncher:
    """Handles launching the application in an external terminal window with maximum size."""

    MIN_WIDTH = 160
    MIN_HEIGHT = 52

    def __init__(self):
        self.system = platform.system()

    def get_script_path(self) -> str:
        """Get the path to the main play.py script."""
        return os.path.join(os.path.dirname(os.path.dirname(__file__)), "play.py")

    def is_running_in_external_terminal(self) -> bool:
        """Check if we're already running in a launched external terminal."""
        return os.environ.get("CARDIO_EXTERNAL_TERMINAL") == "1"

    def mark_external_terminal(self) -> None:
        """Mark the environment to indicate we're in an external terminal."""
        os.environ["CARDIO_EXTERNAL_TERMINAL"] = "1"

    def find_executable(self, names: List[str]) -> Optional[str]:
        """Find the first available executable from a list of names."""
        for name in names:
            path = shutil.which(name)
            if path:
                return path
        return None

    def get_screen_size_linux(self) -> Optional[Tuple[int, int]]:
        """Get screen size on Linux using xdpyinfo or xrandr."""
        try:
            result = subprocess.run(
                ["xdpyinfo"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                for line in result.stdout.split("\n"):
                    if "dimensions:" in line:
                        parts = line.split()
                        for part in parts:
                            if "x" in part and part[0].isdigit():
                                w, h = part.split("x")
                                return int(w), int(h)
        except (subprocess.TimeoutExpired, FileNotFoundError, ValueError):
            pass

        try:
            result = subprocess.run(
                ["xrandr", "--current"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                for line in result.stdout.split("\n"):
                    if " connected" in line and "x" in line:
                        for part in line.split():
                            if "x" in part and part[0].isdigit():
                                resolution = part.split("+")[0]
                                w, h = resolution.split("x")
                                return int(w), int(h)
        except (subprocess.TimeoutExpired, FileNotFoundError, ValueError):
            pass

        return None

    def build_windows_terminal_command(self, script_args: List[str]) -> List[str]:
        """Build command for Windows Terminal (wt.exe)."""
        wt_path = self.find_executable(["wt", "wt.exe"])
        if not wt_path:
            localappdata = os.environ.get("LOCALAPPDATA", "")
            potential_path = os.path.join(
                localappdata,
                "Microsoft",
                "WindowsApps",
                "wt.exe"
            )
            if os.path.exists(potential_path):
                wt_path = potential_path

        if not wt_path:
            raise RuntimeError(
                "Windows Terminal (wt.exe) not found. "
                "Please install Windows Terminal from the Microsoft Store."
            )

        python_exe = sys.executable
        script_path = self.get_script_path()

        cmd = [
            wt_path,
            "--maximized",
            "--",
            python_exe,
            script_path
        ] + script_args

        return cmd

    def build_macos_terminal_command(self, script_args: List[str]) -> Tuple[str, List[str]]:
        """Build AppleScript command for macOS Terminal."""
        python_exe = sys.executable
        script_path = self.get_script_path()

        args_str = " ".join(f'"{arg}"' for arg in script_args)
        full_command = f'"{python_exe}" "{script_path}" {args_str}'.strip()

        applescript = f'''
        tell application "Terminal"
            activate
            set newWindow to do script "export CARDIO_EXTERNAL_TERMINAL=1 && cd \\"{os.path.dirname(script_path)}\\" && {full_command}"
            delay 0.5
            tell application "System Events"
                tell process "Terminal"
                    set frontmost to true
                    keystroke "f" using {{command down, control down}}
                end tell
            end tell
        end tell
        '''
        return "osascript", ["-e", applescript]

    def build_linux_terminal_command(self, script_args: List[str]) -> List[str]:
        """Build command for Linux terminal emulators."""
        python_exe = sys.executable
        script_path = self.get_script_path()

        terminal_configs = [
            {
                "names": ["gnome-terminal"],
                "maximize": ["--maximize"],
                "execute": ["--"],
            },
            {
                "names": ["konsole"],
                "maximize": ["--fullscreen"],
                "execute": ["-e"],
            },
            {
                "names": ["xfce4-terminal"],
                "maximize": ["--maximize"],
                "execute": ["-e"],
                "join_command": True,
            },
            {
                "names": ["mate-terminal"],
                "maximize": ["--maximize"],
                "execute": ["-e"],
                "join_command": True,
            },
            {
                "names": ["xterm"],
                "maximize": ["-maximized"],
                "execute": ["-e"],
            },
            {
                "names": ["urxvt", "rxvt-unicode"],
                "maximize": [],
                "execute": ["-e"],
                "geometry": True,
            },
            {
                "names": ["alacritty"],
                "maximize": [],
                "execute": ["-e"],
                "option_class": True,
            },
            {
                "names": ["kitty"],
                "maximize": ["--start-as=maximized"],
                "execute": [],
            },
            {
                "names": ["tilix"],
                "maximize": ["--maximize"],
                "execute": ["-e"],
                "join_command": True,
            },
            {
                "names": ["terminator"],
                "maximize": ["--maximise"],
                "execute": ["-e"],
                "join_command": True,
            },
        ]

        for config in terminal_configs:
            terminal_path = self.find_executable(config["names"])
            if terminal_path:
                cmd = [terminal_path]

                if config.get("geometry"):
                    screen_size = self.get_screen_size_linux()
                    if screen_size:
                        cols = screen_size[0] // 8
                        rows = screen_size[1] // 16
                        cmd.extend(["-geometry", f"{cols}x{rows}"])

                if config.get("option_class"):
                    cmd.extend(["-o", "window.startup_mode=Maximized"])
                else:
                    cmd.extend(config["maximize"])

                inner_cmd = [python_exe, script_path] + script_args

                if config.get("join_command"):
                    cmd.extend(config["execute"])
                    cmd.append(" ".join(f'"{c}"' for c in inner_cmd))
                else:
                    cmd.extend(config["execute"])
                    cmd.extend(inner_cmd)

                return cmd

        raise RuntimeError(
            "No supported terminal emulator found. "
            "Please install one of: gnome-terminal, konsole, xfce4-terminal, "
            "xterm, alacritty, kitty, tilix, or terminator."
        )

    def launch(self, script_args: Optional[List[str]] = None) -> int:
        """Launch the application in an external terminal with maximum size.

        Args:
            script_args: Additional arguments to pass to play.py

        Returns:
            Exit code from the subprocess (0 on success)
        """
        if script_args is None:
            script_args = []

        self.mark_external_terminal()

        if self.system == "Windows":
            cmd = self.build_windows_terminal_command(script_args)
            env = os.environ.copy()
            env["CARDIO_EXTERNAL_TERMINAL"] = "1"
            env["PYTHONUTF8"] = "1"
            result = subprocess.run(cmd, env=env)
            return result.returncode

        elif self.system == "Darwin":
            executable, args = self.build_macos_terminal_command(script_args)
            result = subprocess.run([executable] + args)
            return result.returncode

        elif self.system == "Linux":
            cmd = self.build_linux_terminal_command(script_args)
            env = os.environ.copy()
            env["CARDIO_EXTERNAL_TERMINAL"] = "1"
            result = subprocess.run(cmd, env=env)
            return result.returncode

        else:
            raise RuntimeError(f"Unsupported operating system: {self.system}")


def should_launch_external() -> bool:
    """Check if we should launch an external terminal."""
    launcher = TerminalLauncher()
    return not launcher.is_running_in_external_terminal()


def launch_in_external_terminal(args: Optional[List[str]] = None) -> int:
    """Launch the application in an external terminal and return exit code."""
    launcher = TerminalLauncher()
    return launcher.launch(args)
