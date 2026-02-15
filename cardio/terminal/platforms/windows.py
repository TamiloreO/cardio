import shutil
import sys
from typing import List, Optional

from ..launcher import TerminalLauncher
from ..config import TerminalConfig


class WindowsTerminalLauncher(TerminalLauncher):
    """Launcher for Windows Terminal (wt.exe).
    
    Uses Windows Terminal instead of cmd.exe because cmd does not properly
    render Unicode characters and emojis.
    """

    EXECUTABLE = "wt.exe"

    def __init__(self, config: Optional[TerminalConfig] = None):
        super().__init__(config)
        self._executable_path: Optional[str] = None

    def is_available(self) -> bool:
        if sys.platform != "win32":
            return False
        self._executable_path = shutil.which(self.EXECUTABLE)
        return self._executable_path is not None

    def get_terminal_name(self) -> str:
        return "Windows Terminal"

    def build_launch_command(self, script_path: str, script_args: List[str]) -> List[str]:
        command = [self._executable_path or self.EXECUTABLE]
        
        if self.config.dimensions.is_maximized():
            command.extend(["--maximized"])
        
        if self.config.title:
            command.extend(["--title", self.config.title])

        command.append("--")
        command.append(sys.executable)
        command.append(script_path)
        command.extend(script_args)

        return command

    def supports_unicode(self) -> bool:
        return True

    def supports_maximized(self) -> bool:
        return True


class WindowsTerminalEnvironmentConfigurator:
    """Configures the Windows Terminal environment for proper emoji rendering."""

    @staticmethod
    def configure_utf8_output() -> None:
        """Configure stdout/stderr for UTF-8 encoding on Windows."""
        if sys.platform != "win32":
            return

        import io
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8')
        if hasattr(sys.stderr, 'reconfigure'):
            sys.stderr.reconfigure(encoding='utf-8')

    @staticmethod
    def set_console_mode() -> bool:
        """Enable virtual terminal processing for proper ANSI/Unicode support."""
        if sys.platform != "win32":
            return False

        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            
            STD_OUTPUT_HANDLE = -11
            ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
            ENABLE_PROCESSED_OUTPUT = 0x0001
            
            handle = kernel32.GetStdHandle(STD_OUTPUT_HANDLE)
            mode = ctypes.c_ulong()
            kernel32.GetConsoleMode(handle, ctypes.byref(mode))
            
            new_mode = mode.value | ENABLE_VIRTUAL_TERMINAL_PROCESSING | ENABLE_PROCESSED_OUTPUT
            kernel32.SetConsoleMode(handle, new_mode)
            return True
        except Exception:
            return False

    @staticmethod
    def set_console_font() -> bool:
        """Attempt to set a font that supports emoji rendering."""
        if sys.platform != "win32":
            return False

        try:
            import ctypes
            
            LF_FACESIZE = 32
            STD_OUTPUT_HANDLE = -11

            class CONSOLE_FONT_INFOEX(ctypes.Structure):
                _fields_ = [
                    ("cbSize", ctypes.c_ulong),
                    ("nFont", ctypes.c_ulong),
                    ("dwFontSize", ctypes.c_long * 2),
                    ("FontFamily", ctypes.c_uint),
                    ("FontWeight", ctypes.c_uint),
                    ("FaceName", ctypes.c_wchar * LF_FACESIZE)
                ]

            font = CONSOLE_FONT_INFOEX()
            font.cbSize = ctypes.sizeof(CONSOLE_FONT_INFOEX)
            font.nFont = 0
            font.dwFontSize[0] = 0
            font.dwFontSize[1] = 16
            font.FontFamily = 54  # FF_MODERN | FIXED_PITCH
            font.FontWeight = 400
            font.FaceName = "Cascadia Code"

            kernel32 = ctypes.windll.kernel32
            handle = kernel32.GetStdHandle(STD_OUTPUT_HANDLE)
            kernel32.SetCurrentConsoleFontEx(handle, False, ctypes.byref(font))
            return True
        except Exception:
            return False

    @classmethod
    def configure_all(cls) -> None:
        """Apply all Windows Terminal configurations."""
        cls.configure_utf8_output()
        cls.set_console_mode()
