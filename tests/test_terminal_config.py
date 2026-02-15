import pytest
from cardio.terminal.config import TerminalConfig, TerminalDimensions


class TestTerminalDimensions:
    def test_maximized_creates_special_dimensions(self):
        dims = TerminalDimensions.maximized()
        assert dims.width == -1
        assert dims.height == -1

    def test_is_maximized_returns_true_for_maximized(self):
        dims = TerminalDimensions.maximized()
        assert dims.is_maximized() is True

    def test_is_maximized_returns_false_for_specific_size(self):
        dims = TerminalDimensions(width=160, height=52)
        assert dims.is_maximized() is False


class TestTerminalConfig:
    def test_default_creates_maximized_config(self):
        config = TerminalConfig.default()
        assert config.dimensions.is_maximized()
        assert config.title == "Cardio"
        assert config.unicode_support is True
