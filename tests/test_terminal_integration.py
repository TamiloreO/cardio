"""Integration tests for the terminal launcher module.

These tests verify end-to-end behavior of the terminal launching system,
including environment variable propagation and the full launch flow.
"""

import os
import sys
import subprocess
import tempfile
import pytest
from unittest.mock import patch, MagicMock

from cardio.terminal import (
    TerminalRunner,
    TerminalConfig,
    TerminalDimensions,
    TerminalLauncherFactory,
    TerminalLauncher,
)
from cardio.terminal.detection import TerminalEnvironmentDetector


class TestEnvironmentVariablePropagation:
    """Integration tests for environment variable propagation to child processes."""

    def test_child_process_receives_environment_variables(self):
        """Verify that environment variables are properly passed to subprocess."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write('''
import os
import sys
marker = os.environ.get("CARDIO_LAUNCHED_TERMINAL", "NOT_SET")
custom = os.environ.get("TEST_CUSTOM_VAR", "NOT_SET")
print(f"MARKER={marker}")
print(f"CUSTOM={custom}")
sys.exit(0)
''')
            script_path = f.name

        try:
            env = os.environ.copy()
            env["CARDIO_LAUNCHED_TERMINAL"] = "1"
            env["TEST_CUSTOM_VAR"] = "test_value"

            result = subprocess.run(
                [sys.executable, script_path],
                env=env,
                capture_output=True,
                text=True,
                timeout=10,
            )

            assert "MARKER=1" in result.stdout
            assert "CUSTOM=test_value" in result.stdout
        finally:
            os.unlink(script_path)

    def test_build_child_environment_includes_marker(self):
        """Verify that _build_child_environment adds the marker variable."""
        runner = TerminalRunner()
        env = runner._build_child_environment()

        assert TerminalEnvironmentDetector.LAUNCHED_ENV_VAR in env
        assert env[TerminalEnvironmentDetector.LAUNCHED_ENV_VAR] == "1"

    def test_build_child_environment_preserves_existing_vars(self):
        """Verify that existing environment variables are preserved."""
        os.environ["TEST_PRESERVE_VAR"] = "preserved_value"
        try:
            runner = TerminalRunner()
            env = runner._build_child_environment()

            assert "TEST_PRESERVE_VAR" in env
            assert env["TEST_PRESERVE_VAR"] == "preserved_value"
        finally:
            del os.environ["TEST_PRESERVE_VAR"]


class TestFullLaunchFlow:
    """Integration tests for the complete launch flow."""

    def test_run_or_relaunch_calls_main_when_already_launched(self):
        """Verify main function is called directly when already in launched terminal."""
        os.environ[TerminalEnvironmentDetector.LAUNCHED_ENV_VAR] = "1"
        try:
            runner = TerminalRunner()
            main_called = []

            def mock_main():
                main_called.append(True)

            runner.run_or_relaunch(mock_main)

            assert len(main_called) == 1
        finally:
            del os.environ[TerminalEnvironmentDetector.LAUNCHED_ENV_VAR]

    def test_launcher_receives_correct_environment(self):
        """Verify that the launcher receives the environment with marker set."""
        mock_launcher = MagicMock(spec=TerminalLauncher)
        mock_launcher.get_terminal_name.return_value = "Mock Terminal"
        mock_launcher.is_available.return_value = True

        captured_env = {}

        def capture_launch(script_path, script_args, env=None):
            captured_env.update(env or {})
            return MagicMock()

        mock_launcher.launch.side_effect = capture_launch

        with patch.object(
            TerminalLauncherFactory, 'create_or_raise', return_value=mock_launcher
        ):
            with patch.object(
                TerminalEnvironmentDetector, 'is_launched_by_cardio', return_value=False
            ):
                with patch.object(
                    TerminalEnvironmentDetector, 'meets_minimum_size', return_value=False
                ):
                    with patch('sys.exit'):
                        runner = TerminalRunner()
                        runner.run_or_relaunch(lambda: None)

        assert TerminalEnvironmentDetector.LAUNCHED_ENV_VAR in captured_env
        assert captured_env[TerminalEnvironmentDetector.LAUNCHED_ENV_VAR] == "1"

    def test_relaunch_loop_prevention(self):
        """Verify that setting marker prevents infinite relaunch loops."""
        # First call: not launched, should want to relaunch
        os.environ.pop(TerminalEnvironmentDetector.LAUNCHED_ENV_VAR, None)
        runner1 = TerminalRunner()

        with patch.object(
            TerminalEnvironmentDetector, 'meets_minimum_size', return_value=False
        ):
            assert runner1.should_relaunch() is True

        # Simulate being in relaunched terminal
        os.environ[TerminalEnvironmentDetector.LAUNCHED_ENV_VAR] = "1"
        try:
            runner2 = TerminalRunner()
            # Even with small terminal, should NOT relaunch since marker is set
            assert runner2.should_relaunch() is False
        finally:
            del os.environ[TerminalEnvironmentDetector.LAUNCHED_ENV_VAR]


class TestLauncherIntegration:
    """Integration tests for platform launcher implementations."""

    def test_launcher_command_includes_script_and_args(self):
        """Verify launcher builds command with correct script path and arguments."""
        launcher = TerminalLauncherFactory.create()
        if launcher is None:
            pytest.skip("No terminal launcher available on this platform")

        command = launcher.build_launch_command(
            "/path/to/script.py",
            ["--arg1", "value1", "--arg2"]
        )

        assert isinstance(command, list)
        assert len(command) > 0
        # The command should contain the script path somewhere
        command_str = " ".join(command)
        assert "/path/to/script.py" in command_str

    def test_launcher_with_maximized_config(self):
        """Verify launcher respects maximized configuration."""
        config = TerminalConfig(
            dimensions=TerminalDimensions.maximized(),
            title="Test Title",
        )
        launcher = TerminalLauncherFactory.create(config)
        if launcher is None:
            pytest.skip("No terminal launcher available on this platform")

        command = launcher.build_launch_command("/path/to/script.py", [])
        command_str = " ".join(command)

        # Should have some form of maximize flag (varies by terminal)
        if launcher.supports_maximized():
            assert any(
                flag in command_str.lower()
                for flag in ["maximize", "maximise", "fullscreen", "--maximized"]
            )


class TestFactoryIntegration:
    """Integration tests for the launcher factory."""

    def test_factory_returns_working_launcher(self):
        """Verify factory returns a launcher that can build valid commands."""
        launcher = TerminalLauncherFactory.create()
        if launcher is None:
            pytest.skip("No terminal launcher available on this platform")

        assert launcher.is_available()
        assert launcher.get_terminal_name()

        # Should be able to build a command without errors
        command = launcher.build_launch_command("test.py", [])
        assert isinstance(command, list)
        assert len(command) > 0

    def test_available_launchers_are_all_functional(self):
        """Verify all available launchers can build commands."""
        launchers = TerminalLauncherFactory.get_available_launchers()

        for launcher in launchers:
            assert launcher.is_available()
            command = launcher.build_launch_command("test.py", ["--test"])
            assert isinstance(command, list)
            assert len(command) > 0
