"""
Terminal Launcher Module
========================

This module provides cross-platform terminal launching capabilities for Cardio,
ensuring the game runs in a properly configured terminal window with adequate
size and Unicode/emoji support.

Architecture Overview
---------------------

The module follows a layered architecture:

1. **Detection Layer** (`detection.py`)
   - `TerminalEnvironmentDetector`: Detects the current terminal environment,
     checks if the terminal meets size requirements, and identifies if the
     process was launched by Cardio's terminal system.

2. **Configuration Layer** (`config.py`)
   - `TerminalConfig`: Holds launch configuration (dimensions, title, etc.)
   - `TerminalDimensions`: Represents terminal window dimensions.

3. **Launcher Layer** (`launcher.py`, `platforms/`)
   - `TerminalLauncher`: Abstract base class defining the launcher interface.
   - Platform-specific implementations:
     - `WindowsTerminalLauncher`: Uses Windows Terminal (wt.exe) for emoji support.
     - `MacOSTerminalLauncher`: Uses Terminal.app or iTerm2 via AppleScript.
     - `LinuxTerminalLauncher`: Supports multiple terminal emulators.

4. **Factory Layer** (`factory.py`)
   - `TerminalLauncherFactory`: Creates the appropriate launcher for the
     current platform.

5. **Orchestration Layer** (`runner.py`)
   - `TerminalRunner`: Coordinates the launch decision and execution.

Flow
----

1. Application starts and creates a `TerminalRunner`.
2. `TerminalRunner.run_or_relaunch()` is called with the main function.
3. The runner checks via `TerminalEnvironmentDetector`:
   - Was this process already launched by Cardio? (via env var check)
   - Does the current terminal meet size requirements?
   - On Windows: Are we in cmd.exe? (needs Windows Terminal for emoji)
4. If relaunch is needed:
   - `TerminalLauncherFactory` creates an appropriate launcher.
   - Environment variables are copied and the marker var is added.
   - The launcher spawns a new terminal with the script.
   - The original process exits.
5. If no relaunch is needed:
   - The main function is called directly.

Environment Variable Propagation
--------------------------------

Child processes receive environment variables via explicit `env` parameter
in `subprocess.Popen()`. The `CARDIO_LAUNCHED_TERMINAL` marker is set in this
copied environment to prevent infinite relaunch loops.

Usage
-----

    from cardio.terminal import TerminalRunner, TerminalConfig, TerminalDimensions

    def main():
        # Your application code
        pass

    config = TerminalConfig(
        dimensions=TerminalDimensions.maximized(),
        title="My App",
    )
    runner = TerminalRunner(config=config)
    runner.run_or_relaunch(main)
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
