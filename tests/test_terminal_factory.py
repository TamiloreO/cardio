import pytest
from cardio.terminal.factory import TerminalLauncherFactory, TerminalNotFoundError
from cardio.terminal.config import TerminalConfig
from cardio.terminal.launcher import TerminalLauncher


class TestTerminalLauncherFactory:
    def test_create_returns_launcher_or_none(self):
        launcher = TerminalLauncherFactory.create()
        assert launcher is None or isinstance(launcher, TerminalLauncher)

    def test_create_with_config(self):
        config = TerminalConfig.default()
        launcher = TerminalLauncherFactory.create(config)
        if launcher:
            assert launcher.config == config

    def test_get_available_launchers_returns_list(self):
        launchers = TerminalLauncherFactory.get_available_launchers()
        assert isinstance(launchers, list)
