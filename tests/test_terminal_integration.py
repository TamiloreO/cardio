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
    TerminalLauncherFactory,
    TerminalConfig,
    TerminalDimensions,
    TerminalEnvironmentDetector,
)
from cardio.terminal.launcher import TerminalLauncher


class MockTerminalLauncher(TerminalLauncher):
    """Mock launcher that captures launch parameters for testing."""

    def __init__(self, config=None):
        super().__init__(config)
        self.launch_calls = []
        self.last_env = None
        self.last_script = None
        self.last_args = None

    def is_available(self) -> bool:
        return True

    def get_terminal_name(self) -> str:
        return "Mock Terminal"

    def build_launch_command(self, script_path, script_args):
        return ["mock", script_path] + script_args

    def launch(self, script_path, script_args=None, env=None):
        self.last_script = script_path
        self.last_args = script_args or []
        self.last_env = env
        self.launch_calls.append({
            "script": script_path,
            "args": script_args,
            "env": env,
        })
        return MagicMock()


class TestEnvironmentPropagationIntegration:
    """Tests that environment variables are properly passed to child processes."""

    def test_environment_includes_launched_marker(self):
        """Verify that CARDIO_LAUNCHED_TERMINAL is set in child environment."""
        mock_launcher = MockTerminalLauncher()
        runner = TerminalRunner()

        env = runner._build_child_environment()

        assert TerminalEnvironmentDetector.LAUNCHED_ENV_VAR in env
        assert env[TerminalEnvironmentDetector.LAUNCHED_ENV_VAR] == "1"

    def test_environment_preserves_existing_variables(self):
        """Verify that existing environment variables are preserved."""
        os.environ["TEST_CARDIO_VAR"] = "test_value"
        try:
            runner = TerminalRunner()
            env = runner._build_child_environment()

            assert "TEST_CARDIO_VAR" in env
            assert env["TEST_CARDIO_VAR"] == "test_value"
        finally:
            del os.environ["TEST_CARDIO_VAR"]

    def test_launcher_receives_environment_dict(self):
        """Verify that the launcher receives the environment dictionary."""
        mock_launcher = MockTerminalLauncher()
        
        with patch.object(
            TerminalLauncherFactory, 'create_or_raise', return_value=mock_launcher
        ):
            runner = TerminalRunner()
            
            with pytest.raises(SystemExit):
                runner._launch_external(mock_launcher, "/path/to/script.py", ["--arg"])

        assert mock_launcher.last_env is not None
        assert isinstance(mock_launcher.last_env, dict)
        assert TerminalEnvironmentDetector.LAUNCHED_ENV_VAR in mock_launcher.last_env

    def test_child_process_receives_environment_via_popen(self):
        """Integration test: verify subprocess.Popen receives env parameter."""
        mock_launcher = MockTerminalLauncher()
        
        with patch('subprocess.Popen') as mock_popen:
            mock_popen.return_value = MagicMock()
            
            env = {"TEST_VAR": "value", "PATH": "/usr/bin"}
            TerminalLauncher.launch(mock_launcher, "script.py", ["arg"], env=env)

            mock_popen.assert_called_once()
            call_kwargs = mock_popen.call_args
            assert call_kwargs.kwargs.get('env') == env


class TestFullLaunchFlowIntegration:
    """End-to-end tests for the complete terminal launch flow."""

    def test_no_relaunch_when_already_launched(self):
        """Verify that we don't relaunch if already launched by Cardio."""
        os.environ[TerminalEnvironmentDetector.LAUNCHED_ENV_VAR] = "1"
        try:
            main_called = []

            def mock_main():
                main_called.append(True)

            runner = TerminalRunner()
            runner.run_or_relaunch(mock_main)

            assert len(main_called) == 1
        finally:
            del os.environ[TerminalEnvironmentDetector.LAUNCHED_ENV_VAR]

    def test_relaunch_when_terminal_too_small(self):
        """Verify relaunch is triggered when terminal is below minimum size."""
        os.environ.pop(TerminalEnvironmentDetector.LAUNCHED_ENV_VAR, None)

        mock_launcher = MockTerminalLauncher()
        main_called = []

        def mock_main():
            main_called.append(True)

        with patch.object(
            TerminalEnvironmentDetector, 'is_launched_by_cardio', return_value=False
        ), patch.object(
            TerminalEnvironmentDetector, 'is_cmd_exe', return_value=False
        ), patch.object(
            TerminalEnvironmentDetector, 'meets_minimum_size', return_value=False
        ), patch.object(
            TerminalLauncherFactory, 'create_or_raise', return_value=mock_launcher
        ), patch('sys.exit') as mock_exit:
            runner = TerminalRunner()
            runner.run_or_relaunch(mock_main)

            # Main should NOT be called (we're relaunching)
            assert len(main_called) == 0
            # Launcher should have been called
            assert len(mock_launcher.launch_calls) == 1
            # sys.exit should be called to terminate original process
            mock_exit.assert_called_once_with(0)

    def test_full_flow_with_script_args(self):
        """Verify script arguments are passed through the full flow."""
        os.environ.pop(TerminalEnvironmentDetector.LAUNCHED_ENV_VAR, None)

        mock_launcher = MockTerminalLauncher()

        with patch.object(
            TerminalEnvironmentDetector, 'is_launched_by_cardio', return_value=False
        ), patch.object(
            TerminalEnvironmentDetector, 'meets_minimum_size', return_value=False
        ), patch.object(
            TerminalEnvironmentDetector, 'is_cmd_exe', return_value=False
        ), patch.object(
            TerminalLauncherFactory, 'create_or_raise', return_value=mock_launcher
        ), patch('sys.exit'):
            runner = TerminalRunner()
            runner.run_or_relaunch(
                lambda: None,
                script_path="/my/script.py",
                script_args=["--reset", "--human-name", "Test"]
            )

            assert mock_launcher.last_script == "/my/script.py"
            assert mock_launcher.last_args == ["--reset", "--human-name", "Test"]

    def test_fallback_to_main_when_no_terminal_found(self):
        """Verify graceful fallback when no terminal launcher is available."""
        from cardio.terminal.factory import TerminalNotFoundError

        os.environ.pop(TerminalEnvironmentDetector.LAUNCHED_ENV_VAR, None)

        main_called = []

        def mock_main():
            main_called.append(True)

        with patch.object(
            TerminalEnvironmentDetector, 'is_launched_by_cardio', return_value=False
        ), patch.object(
            TerminalEnvironmentDetector, 'meets_minimum_size', return_value=False
        ), patch.object(
            TerminalEnvironmentDetector, 'is_cmd_exe', return_value=False
        ), patch.object(
            TerminalLauncherFactory, 'create_or_raise',
            side_effect=TerminalNotFoundError("No terminal found")
        ):
            runner = TerminalRunner()
            # Should not raise, should fall back to running main
            runner.run_or_relaunch(mock_main)

            assert len(main_called) == 1

    def test_config_passed_to_factory(self):
        """Verify that terminal config is passed through to factory."""
        os.environ.pop(TerminalEnvironmentDetector.LAUNCHED_ENV_VAR, None)

        custom_config = TerminalConfig(
            dimensions=TerminalDimensions(width=200, height=60),
            title="Custom Title",
        )
        mock_launcher = MockTerminalLauncher(custom_config)
        captured_config = []

        def capture_factory(config):
            captured_config.append(config)
            return mock_launcher

        with patch.object(
            TerminalEnvironmentDetector, 'is_launched_by_cardio', return_value=False
        ), patch.object(
            TerminalEnvironmentDetector, 'meets_minimum_size', return_value=False
        ), patch.object(
            TerminalEnvironmentDetector, 'is_cmd_exe', return_value=False
        ), patch.object(
            TerminalLauncherFactory, 'create_or_raise', side_effect=capture_factory
        ), patch('sys.exit'):
            runner = TerminalRunner(config=custom_config)
            runner.run_or_relaunch(lambda: None)

            assert len(captured_config) == 1
            assert captured_config[0] == custom_config
