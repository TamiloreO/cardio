import os
import sys
from typing import Callable, Dict, List, Optional

from .config import TerminalConfig
from .factory import TerminalLauncherFactory, TerminalNotFoundError
from .detection import TerminalEnvironmentDetector


class TerminalRunner:
    """Orchestrates launching the application in an appropriate terminal.
    
    This class determines whether the current terminal environment is suitable
    for running the application, and if not, relaunches in an external terminal
    with proper configuration (maximized window, unicode support, etc.).
    
    Environment variables are explicitly passed to child processes using
    os.environ.copy() to ensure reliable propagation across all platforms.
    """

    def __init__(
        self,
        config: Optional[TerminalConfig] = None,
        detector: Optional[TerminalEnvironmentDetector] = None,
        factory: Optional[TerminalLauncherFactory] = None,
    ):
        self.config = config or TerminalConfig.default()
        self.detector = detector or TerminalEnvironmentDetector()
        self.factory = factory or TerminalLauncherFactory()

    def should_relaunch(self) -> bool:
        """Determine if we need to relaunch in a new terminal."""
        # Already launched by us
        if self.detector.is_launched_by_cardio():
            return False
        
        # On Windows, avoid cmd.exe for emoji support
        if sys.platform == "win32" and self.detector.is_cmd_exe():
            return True
        
        # Check terminal size requirements
        if not self.detector.meets_minimum_size():
            return True
        
        return False

    def run_or_relaunch(
        self,
        main_func: Callable[[], None],
        script_path: Optional[str] = None,
        script_args: Optional[List[str]] = None,
    ) -> None:
        """Run the main function directly or relaunch in a new terminal if needed."""
        if not self.should_relaunch():
            self._configure_environment()
            main_func()
            return

        effective_script = script_path or sys.argv[0]
        effective_args = script_args if script_args is not None else sys.argv[1:]

        try:
            launcher = self.factory.create_or_raise(self.config)
            self._launch_external(launcher, effective_script, effective_args)
        except TerminalNotFoundError as e:
            print(f"Warning: {e}")
            print("Running in current terminal...")
            self._configure_environment()
            main_func()

    def _build_child_environment(self) -> Dict[str, str]:
        """Build environment dictionary for child process.
        
        Creates a copy of the current environment and adds the marker
        variable to indicate the child was launched by Cardio.
        """
        env = os.environ.copy()
        env[TerminalEnvironmentDetector.LAUNCHED_ENV_VAR] = "1"
        return env

    def _launch_external(
        self, launcher, script_path: str, script_args: List[str]
    ) -> None:
        """Launch the script in an external terminal with proper environment."""
        env = self._build_child_environment()
        
        print(f"Launching in {launcher.get_terminal_name()}...")
        launcher.launch(script_path, script_args, env=env)
        
        # Exit this process - the new terminal will run the game
        sys.exit(0)

    def _configure_environment(self) -> None:
        """Configure the current terminal environment."""
        if sys.platform == "win32":
            from .platforms.windows import WindowsTerminalEnvironmentConfigurator
            WindowsTerminalEnvironmentConfigurator.configure_all()
