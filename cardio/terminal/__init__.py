"""
Terminal Launcher Module
========================

This module provides cross-platform terminal launching capabilities for Cardio.
It automatically detects the current terminal environment and relaunches the
application in an appropriate external terminal when needed.

Architecture Overview
---------------------

The module follows a layered architecture:

1. **Detection Layer** (`detection.py`)
   - `TerminalEnvironmentDetector`: Detects current terminal type, size, and
     capabilities. Checks if the process was already launched by Cardio.

2. **Configuration Layer** (`config.py`)
   - `TerminalConfig`: Configuration for terminal launch (dimensions, title, etc.)
   - `TerminalDimensions`: Represents terminal size or maximized state.

3. **Launcher Layer** (`launcher.py`, `platforms/`)
   - `TerminalLauncher`: Abstract base class defining the launcher interface.
   - Platform implementations:
     - `WindowsTerminalLauncher`: Uses Windows Terminal (wt.exe) for emoji support.
     - `MacOSTerminalLauncher`: Uses Terminal.app or iTerm2 via AppleScript.
     - `LinuxTerminalLauncher`: Supports multiple emulators (kitty, gnome-terminal, etc.)

4. **Factory Layer** (`factory.py`)
   - `TerminalLauncherFactory`: Creates appropriate launcher for current platform.

5. **Runner Layer** (`runner.py`)
   - `TerminalRunner`: Orchestrates the decision to run in-place or relaunch.

Flow
----

1. Application starts and creates a `TerminalRunner`.
2. Runner checks `should_relaunch()`:
   - If already launched by Cardio (env var set), run in place.
   - If on Windows cmd.exe, relaunch for emoji support.
   - If terminal too small, relaunch maximized.
3. If relaunching:
   - Factory creates appropriate platform launcher.
   - Environment is copied via `os.environ.copy()` with marker variable added.
   - Launcher spawns new terminal process with environment passed explicitly.
   - Original process exits.
4. If not relaunching:
   - Configure current environment (e.g., UTF-8 on Windows).
   - Run the main function directly.

Environment Variable Propagation
--------------------------------

Environment variables are passed explicitly to child processes using
`os.environ.copy()` to ensure reliable propagation across all platforms.
The `CARDIO_LAUNCHED_TERMINAL` marker variable prevents infinite relaunch loops.
"""

from .launcher import TerminalLauncher
from .factory import TerminalLauncherFactory, TerminalNotFoundError
from .config import TerminalConfig, TerminalDimensions
from .detection import TerminalEnvironmentDetector
from .runner import TerminalRunner

__all__ = [
    "TerminalLauncher",
    "TerminalLauncherFactory",
    "TerminalNotFoundError",
    "TerminalConfig",
    "TerminalDimensions",
    "TerminalEnvironmentDetector",
    "TerminalRunner",
]
