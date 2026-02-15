"""Tests for the terminal launcher module."""

import os
import sys
import pytest
from unittest.mock import patch, MagicMock
from cardio.terminal_launcher import (
    TerminalLauncher,
    should_launch_external,
    launch_in_external_terminal,
)


class TestTerminalLauncher:
    """Unit tests for TerminalLauncher class."""

    def test_init_detects_system(self):
        launcher = TerminalLauncher()
        assert launcher.system in ("Windows", "Linux", "Darwin", "FreeBSD")

    def test_get_script_path_returns_valid_path(self):
        launcher = TerminalLauncher()
        script_path = launcher.get_script_path()
        assert script_path.endswith("play.py")
        assert os.path.exists(script_path)

    def test_is_running_in_external_terminal_false_by_default(self):
        launcher = TerminalLauncher()
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("CARDIO_EXTERNAL_TERMINAL", None)
            assert launcher.is_running_in_external_terminal() is False

    def test_is_running_in_external_terminal_true_when_set(self):
        launcher = TerminalLauncher()
        with patch.dict(os.environ, {"CARDIO_EXTERNAL_TERMINAL": "1"}):
            assert launcher.is_running_in_external_terminal() is True

    def test_mark_external_terminal_sets_env_var(self):
        launcher = TerminalLauncher()
        original = os.environ.get("CARDIO_EXTERNAL_TERMINAL")
        try:
            launcher.mark_external_terminal()
            assert os.environ.get("CARDIO_EXTERNAL_TERMINAL") == "1"
        finally:
            if original is None:
                os.environ.pop("CARDIO_EXTERNAL_TERMINAL", None)
            else:
                os.environ["CARDIO_EXTERNAL_TERMINAL"] = original

    def test_find_executable_returns_none_for_nonexistent(self):
        launcher = TerminalLauncher()
        result = launcher.find_executable(["nonexistent_binary_xyz123"])
        assert result is None

    def test_find_executable_returns_path_for_python(self):
        launcher = TerminalLauncher()
        result = launcher.find_executable(["python3", "python"])
        assert result is not None
        assert "python" in result.lower()

    def test_find_executable_tries_multiple_names(self):
        launcher = TerminalLauncher()
        result = launcher.find_executable([
            "nonexistent_xyz",
            "python3",
            "python"
        ])
        assert result is not None


class TestWindowsTerminalCommand:
    """Tests for Windows Terminal command building."""

    def test_build_windows_terminal_command_with_wt_found(self):
        launcher = TerminalLauncher()
        launcher.system = "Windows"

        with patch.object(launcher, "find_executable", return_value="/path/to/wt.exe"):
            cmd = launcher.build_windows_terminal_command(["--reset"])

        assert cmd[0] == "/path/to/wt.exe"
        assert "--maximized" in cmd
        assert "--" in cmd
        assert sys.executable in cmd
        assert "--reset" in cmd

    def test_build_windows_terminal_command_raises_when_not_found(self):
        launcher = TerminalLauncher()
        launcher.system = "Windows"

        with patch.object(launcher, "find_executable", return_value=None):
            with patch.dict(os.environ, {"LOCALAPPDATA": "/nonexistent"}):
                with pytest.raises(RuntimeError, match="Windows Terminal"):
                    launcher.build_windows_terminal_command([])

    def test_build_windows_terminal_command_checks_localappdata(self):
        launcher = TerminalLauncher()
        launcher.system = "Windows"

        with patch.object(launcher, "find_executable", return_value=None):
            with patch.dict(os.environ, {"LOCALAPPDATA": "/test/path"}):
                with patch("os.path.exists", return_value=True):
                    cmd = launcher.build_windows_terminal_command([])
                    expected_path = "/test/path/Microsoft/WindowsApps/wt.exe"
                    assert cmd[0] == expected_path


class TestMacOSTerminalCommand:
    """Tests for macOS Terminal command building."""

    def test_build_macos_terminal_command_returns_osascript(self):
        launcher = TerminalLauncher()
        launcher.system = "Darwin"

        executable, args = launcher.build_macos_terminal_command(["--reset"])

        assert executable == "osascript"
        assert len(args) == 2
        assert args[0] == "-e"
        assert "Terminal" in args[1]
        assert "CARDIO_EXTERNAL_TERMINAL=1" in args[1]

    def test_build_macos_terminal_command_includes_fullscreen(self):
        launcher = TerminalLauncher()
        launcher.system = "Darwin"

        _, args = launcher.build_macos_terminal_command([])

        applescript = args[1]
        assert "keystroke" in applescript
        assert "command down" in applescript


class TestLinuxTerminalCommand:
    """Tests for Linux terminal command building."""

    def test_build_linux_terminal_command_gnome_terminal(self):
        launcher = TerminalLauncher()
        launcher.system = "Linux"

        def mock_find(names):
            if "gnome-terminal" in names:
                return "/usr/bin/gnome-terminal"
            return None

        with patch.object(launcher, "find_executable", side_effect=mock_find):
            cmd = launcher.build_linux_terminal_command(["--reset"])

        assert cmd[0] == "/usr/bin/gnome-terminal"
        assert "--maximize" in cmd
        assert "--" in cmd
        assert "--reset" in cmd

    def test_build_linux_terminal_command_konsole(self):
        launcher = TerminalLauncher()
        launcher.system = "Linux"

        def mock_find(names):
            if "konsole" in names:
                return "/usr/bin/konsole"
            return None

        with patch.object(launcher, "find_executable", side_effect=mock_find):
            cmd = launcher.build_linux_terminal_command([])

        assert cmd[0] == "/usr/bin/konsole"
        assert "--fullscreen" in cmd
        assert "-e" in cmd

    def test_build_linux_terminal_command_xterm(self):
        launcher = TerminalLauncher()
        launcher.system = "Linux"

        def mock_find(names):
            if "xterm" in names:
                return "/usr/bin/xterm"
            return None

        with patch.object(launcher, "find_executable", side_effect=mock_find):
            cmd = launcher.build_linux_terminal_command([])

        assert cmd[0] == "/usr/bin/xterm"
        assert "-maximized" in cmd
        assert "-e" in cmd

    def test_build_linux_terminal_command_kitty(self):
        launcher = TerminalLauncher()
        launcher.system = "Linux"

        def mock_find(names):
            if "kitty" in names:
                return "/usr/bin/kitty"
            return None

        with patch.object(launcher, "find_executable", side_effect=mock_find):
            cmd = launcher.build_linux_terminal_command([])

        assert cmd[0] == "/usr/bin/kitty"
        assert "--start-as=maximized" in cmd

    def test_build_linux_terminal_command_alacritty(self):
        launcher = TerminalLauncher()
        launcher.system = "Linux"

        def mock_find(names):
            if "alacritty" in names:
                return "/usr/bin/alacritty"
            return None

        with patch.object(launcher, "find_executable", side_effect=mock_find):
            cmd = launcher.build_linux_terminal_command([])

        assert cmd[0] == "/usr/bin/alacritty"
        assert "-o" in cmd
        assert "window.startup_mode=Maximized" in cmd

    def test_build_linux_terminal_command_raises_when_none_found(self):
        launcher = TerminalLauncher()
        launcher.system = "Linux"

        with patch.object(launcher, "find_executable", return_value=None):
            with pytest.raises(RuntimeError, match="No supported terminal"):
                launcher.build_linux_terminal_command([])

    def test_build_linux_terminal_command_xfce4_joins_command(self):
        launcher = TerminalLauncher()
        launcher.system = "Linux"

        def mock_find(names):
            if "xfce4-terminal" in names:
                return "/usr/bin/xfce4-terminal"
            return None

        with patch.object(launcher, "find_executable", side_effect=mock_find):
            cmd = launcher.build_linux_terminal_command(["--reset"])

        assert cmd[0] == "/usr/bin/xfce4-terminal"
        assert "--maximize" in cmd
        last_arg = cmd[-1]
        assert "python" in last_arg.lower()
        assert "play.py" in last_arg


class TestScreenSizeLinux:
    """Tests for Linux screen size detection."""

    def test_get_screen_size_linux_with_xdpyinfo(self):
        launcher = TerminalLauncher()

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "  dimensions:    1920x1080 pixels\n"

        with patch("subprocess.run", return_value=mock_result):
            size = launcher.get_screen_size_linux()

        assert size == (1920, 1080)

    def test_get_screen_size_linux_with_xrandr(self):
        launcher = TerminalLauncher()

        def mock_run(cmd, **kwargs):
            result = MagicMock()
            if "xdpyinfo" in cmd:
                result.returncode = 1
                result.stdout = ""
            else:
                result.returncode = 0
                result.stdout = "HDMI-1 connected 2560x1440+0+0\n"
            return result

        with patch("subprocess.run", side_effect=mock_run):
            size = launcher.get_screen_size_linux()

        assert size == (2560, 1440)

    def test_get_screen_size_linux_returns_none_on_failure(self):
        launcher = TerminalLauncher()

        with patch("subprocess.run", side_effect=FileNotFoundError):
            size = launcher.get_screen_size_linux()

        assert size is None


class TestLaunchMethod:
    """Tests for the main launch method."""

    def test_launch_windows(self):
        launcher = TerminalLauncher()
        launcher.system = "Windows"

        mock_result = MagicMock()
        mock_result.returncode = 0

        with patch.object(launcher, "build_windows_terminal_command", return_value=["wt", "--maximized"]):
            with patch("subprocess.run", return_value=mock_result) as mock_run:
                result = launcher.launch(["--reset"])

        assert result == 0
        mock_run.assert_called_once()
        call_kwargs = mock_run.call_args
        assert call_kwargs[1]["env"]["CARDIO_EXTERNAL_TERMINAL"] == "1"
        assert call_kwargs[1]["env"]["PYTHONUTF8"] == "1"

    def test_launch_macos(self):
        launcher = TerminalLauncher()
        launcher.system = "Darwin"

        mock_result = MagicMock()
        mock_result.returncode = 0

        with patch.object(launcher, "build_macos_terminal_command", return_value=("osascript", ["-e", "script"])):
            with patch("subprocess.run", return_value=mock_result) as mock_run:
                result = launcher.launch([])

        assert result == 0
        mock_run.assert_called_once()

    def test_launch_linux(self):
        launcher = TerminalLauncher()
        launcher.system = "Linux"

        mock_result = MagicMock()
        mock_result.returncode = 0

        with patch.object(launcher, "build_linux_terminal_command", return_value=["gnome-terminal", "--maximize"]):
            with patch("subprocess.run", return_value=mock_result) as mock_run:
                result = launcher.launch([])

        assert result == 0
        mock_run.assert_called_once()
        call_kwargs = mock_run.call_args
        assert call_kwargs[1]["env"]["CARDIO_EXTERNAL_TERMINAL"] == "1"

    def test_launch_unsupported_os(self):
        launcher = TerminalLauncher()
        launcher.system = "UnknownOS"

        with pytest.raises(RuntimeError, match="Unsupported operating system"):
            launcher.launch([])

    def test_launch_with_none_args(self):
        launcher = TerminalLauncher()
        launcher.system = "Linux"

        mock_result = MagicMock()
        mock_result.returncode = 0

        with patch.object(launcher, "build_linux_terminal_command", return_value=["cmd"]) as mock_build:
            with patch("subprocess.run", return_value=mock_result):
                launcher.launch(None)

        mock_build.assert_called_once_with([])


class TestHelperFunctions:
    """Tests for module-level helper functions."""

    def test_should_launch_external_false_when_env_set(self):
        with patch.dict(os.environ, {"CARDIO_EXTERNAL_TERMINAL": "1"}):
            assert should_launch_external() is False

    def test_should_launch_external_true_when_env_not_set(self):
        env = os.environ.copy()
        env.pop("CARDIO_EXTERNAL_TERMINAL", None)
        with patch.dict(os.environ, env, clear=True):
            assert should_launch_external() is True

    def test_launch_in_external_terminal_calls_launcher(self):
        mock_launcher = MagicMock()
        mock_launcher.launch.return_value = 0

        with patch("cardio.terminal_launcher.TerminalLauncher", return_value=mock_launcher):
            result = launch_in_external_terminal(["--reset"])

        assert result == 0
        mock_launcher.launch.assert_called_once_with(["--reset"])


class TestIntegration:
    """Integration tests for terminal launcher."""

    def test_full_launch_flow_marks_environment(self):
        launcher = TerminalLauncher()
        original = os.environ.get("CARDIO_EXTERNAL_TERMINAL")

        try:
            os.environ.pop("CARDIO_EXTERNAL_TERMINAL", None)

            assert not launcher.is_running_in_external_terminal()

            launcher.mark_external_terminal()

            assert launcher.is_running_in_external_terminal()

        finally:
            if original is None:
                os.environ.pop("CARDIO_EXTERNAL_TERMINAL", None)
            else:
                os.environ["CARDIO_EXTERNAL_TERMINAL"] = original

    def test_script_path_is_in_cardio_directory(self):
        launcher = TerminalLauncher()
        script_path = launcher.get_script_path()

        parent_dir = os.path.basename(os.path.dirname(script_path))
        assert parent_dir == "cardio-main" or "cardio" in parent_dir.lower()

    def test_minimum_dimensions_defined(self):
        assert TerminalLauncher.MIN_WIDTH == 160
        assert TerminalLauncher.MIN_HEIGHT == 52

    def test_command_includes_python_executable(self):
        launcher = TerminalLauncher()

        if launcher.system == "Windows":
            with patch.object(launcher, "find_executable", return_value="wt.exe"):
                cmd = launcher.build_windows_terminal_command([])
                assert sys.executable in cmd

        elif launcher.system == "Linux":
            with patch.object(launcher, "find_executable", return_value="/usr/bin/xterm"):
                cmd = launcher.build_linux_terminal_command([])
                assert sys.executable in cmd
