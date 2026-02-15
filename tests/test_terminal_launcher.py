import sys
import pytest
from unittest.mock import patch, MagicMock
from cardio.terminal.config import TerminalConfig, TerminalDimensions
from cardio.terminal.platforms.windows import WindowsTerminalLauncher
from cardio.terminal.platforms.linux import LinuxTerminalLauncher, TerminalCommandBuilder
from cardio.terminal.platforms.macos import MacOSTerminalLauncher


class TestWindowsTerminalLauncher:
    def test_get_terminal_name(self):
        launcher = WindowsTerminalLauncher()
        assert launcher.get_terminal_name() == "Windows Terminal"

    def test_supports_unicode(self):
        launcher = WindowsTerminalLauncher()
        assert launcher.supports_unicode() is True

    @patch("sys.platform", "win32")
    @patch("shutil.which")
    def test_is_available_when_wt_exists(self, mock_which):
        mock_which.return_value = "/path/to/wt.exe"
        launcher = WindowsTerminalLauncher()
        assert launcher.is_available() is True

    @patch("sys.platform", "linux")
    def test_is_not_available_on_linux(self):
        launcher = WindowsTerminalLauncher()
        assert launcher.is_available() is False


class TestLinuxTerminalLauncher:
    @patch("sys.platform", "linux")
    @patch("shutil.which")
    def test_is_available_with_gnome_terminal(self, mock_which):
        def which_side_effect(cmd):
            return "/usr/bin/gnome-terminal" if cmd == "gnome-terminal" else None
        mock_which.side_effect = which_side_effect
        
        launcher = LinuxTerminalLauncher()
        assert launcher.is_available() is True
        assert launcher.get_terminal_name() == "GNOME Terminal"

    @patch("sys.platform", "win32")
    def test_is_not_available_on_windows(self):
        launcher = LinuxTerminalLauncher()
        assert launcher.is_available() is False


class TestTerminalCommandBuilder:
    def test_build_gnome_terminal_maximized(self):
        config = TerminalConfig(
            dimensions=TerminalDimensions.maximized(),
            title="Test",
        )
        builder = TerminalCommandBuilder("gnome-terminal", config, "/path/script.py", [])
        cmd = builder.build()
        
        assert "gnome-terminal" in cmd
        assert "--maximize" in cmd
        assert "--title" in cmd


class TestMacOSTerminalLauncher:
    @patch("sys.platform", "darwin")
    @patch("os.path.exists")
    def test_is_available_with_terminal_app(self, mock_exists):
        def exists_side_effect(path):
            return path == "/Applications/Utilities/Terminal.app"
        mock_exists.side_effect = exists_side_effect
        
        launcher = MacOSTerminalLauncher()
        assert launcher.is_available() is True
        assert launcher.get_terminal_name() == "Terminal.app"

    @patch("sys.platform", "linux")
    def test_is_not_available_on_linux(self):
        launcher = MacOSTerminalLauncher()
        assert launcher.is_available() is False
