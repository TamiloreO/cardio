import os
import sys
from typing import List, Optional, Callable

from .config import TerminalConfig
from .factory import TerminalLauncherFactory, TerminalNotFoundError
from .detection import TerminalEnvironmentDetector


class TerminalRunner:
    """Orchestrates launching the application in an appropriate terminal."""

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

    def _launch_external(
        self, launcher, script_path: str, script_args: List[str]
    ) -> None:
        """Launch the script in an external terminal."""
        # Set environment variable so the new process knows it was launched by us
        env_script = self._create_env_wrapper_script(script_path, script_args)
        
        print(f"Launching in {launcher.get_terminal_name()}...")
        process = launcher.launch(env_script, script_args)
        
        # Exit this process - the new terminal will run the game
        sys.exit(0)

    def _create_env_wrapper_script(
        self, script_path: str, script_args: List[str]
    ) -> str:
        """Return the script path, environment will be set via subprocess."""
        # We'll set the environment variable in the command itself
        os.environ[TerminalEnvironmentDetector.LAUNCHED_ENV_VAR] = "1"
        return script_path

    def _configure_environment(self) -> None:
        """Configure the current terminal environment."""
        if sys.platform == "win32":
            from .platforms.windows import WindowsTerminalEnvironmentConfigurator
            WindowsTerminalEnvironmentConfigurator.configure_all()


class TerminalRunnerBuilder:
    """Builder for creating configured TerminalRunner instances."""

    def __init__(self):
        self._config: Optional[TerminalConfig] = None
        self._detector: Optional[TerminalEnvironmentDetector] = None
        self._factory: Optional[TerminalLauncherFactory] = None

    def with_config(self, config: TerminalConfig) -> "TerminalRunnerBuilder":
        self._config = config
        return self

    def with_detector(
        self, detector: TerminalEnvironmentDetector
    ) -> "TerminalRunnerBuilder":
        self._detector = detector
        return self

    def with_factory(self, factory: TerminalLauncherFactory) -> "TerminalRunnerBuilder":
        self._factory = factory
        return self

    def build(self) -> TerminalRunner:
        return TerminalRunner(
            config=self._config,
            detector=self._detector,
            factory=self._factory,
        )
