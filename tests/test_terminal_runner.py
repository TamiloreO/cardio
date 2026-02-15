import os
import sys
import pytest
from unittest.mock import patch, MagicMock
from cardio.terminal.runner import TerminalRunner
from cardio.terminal.config import TerminalConfig
from cardio.terminal.detection import TerminalEnvironmentDetector


class TestTerminalRunner:
    def test_should_not_relaunch_when_already_launched(self):
        os.environ[TerminalEnvironmentDetector.LAUNCHED_ENV_VAR] = "1"
        try:
            runner = TerminalRunner()
            assert runner.should_relaunch() is False
        finally:
            os.environ.pop(TerminalEnvironmentDetector.LAUNCHED_ENV_VAR, None)

    @patch.object(TerminalEnvironmentDetector, "is_launched_by_cardio", return_value=False)
    @patch.object(TerminalEnvironmentDetector, "is_cmd_exe", return_value=False)
    @patch.object(TerminalEnvironmentDetector, "meets_minimum_size", return_value=True)
    def test_should_not_relaunch_when_terminal_meets_requirements(
        self, mock_size, mock_cmd, mock_launched
    ):
        runner = TerminalRunner()
        assert runner.should_relaunch() is False

    @patch.object(TerminalEnvironmentDetector, "is_launched_by_cardio", return_value=False)
    @patch.object(TerminalEnvironmentDetector, "is_cmd_exe", return_value=False)
    @patch.object(TerminalEnvironmentDetector, "meets_minimum_size", return_value=False)
    def test_should_relaunch_when_terminal_too_small(
        self, mock_size, mock_cmd, mock_launched
    ):
        runner = TerminalRunner()
        assert runner.should_relaunch() is True

    @patch("sys.platform", "win32")
    @patch.object(TerminalEnvironmentDetector, "is_launched_by_cardio", return_value=False)
    @patch.object(TerminalEnvironmentDetector, "is_cmd_exe", return_value=True)
    def test_should_relaunch_on_windows_cmd(self, mock_cmd, mock_launched):
        runner = TerminalRunner()
        assert runner.should_relaunch() is True
