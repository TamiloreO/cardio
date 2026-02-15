import os
import pytest
from cardio.terminal.detection import TerminalEnvironmentDetector


class TestTerminalEnvironmentDetector:
    def test_is_launched_by_cardio_false_by_default(self):
        os.environ.pop(TerminalEnvironmentDetector.LAUNCHED_ENV_VAR, None)
        assert TerminalEnvironmentDetector.is_launched_by_cardio() is False

    def test_mark_as_launched_sets_env_var(self):
        os.environ.pop(TerminalEnvironmentDetector.LAUNCHED_ENV_VAR, None)
        TerminalEnvironmentDetector.mark_as_launched()
        assert TerminalEnvironmentDetector.is_launched_by_cardio() is True
        os.environ.pop(TerminalEnvironmentDetector.LAUNCHED_ENV_VAR, None)

    def test_get_terminal_size_returns_tuple(self):
        size = TerminalEnvironmentDetector.get_terminal_size()
        assert isinstance(size, tuple)
        assert len(size) == 2

    def test_meets_minimum_size_with_custom_values(self):
        result = TerminalEnvironmentDetector.meets_minimum_size(min_width=1, min_height=1)
        assert isinstance(result, bool)
