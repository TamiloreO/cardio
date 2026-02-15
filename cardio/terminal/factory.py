import sys
from typing import List, Optional, Type

from .launcher import TerminalLauncher
from .config import TerminalConfig
from .platforms.windows import WindowsTerminalLauncher
from .platforms.macos import MacOSTerminalLauncher
from .platforms.linux import LinuxTerminalLauncher


class TerminalLauncherFactory:
    """Factory for creating platform-appropriate terminal launchers."""

    _launcher_registry: List[Type[TerminalLauncher]] = [
        WindowsTerminalLauncher,
        MacOSTerminalLauncher,
        LinuxTerminalLauncher,
    ]

    @classmethod
    def register_launcher(cls, launcher_class: Type[TerminalLauncher]) -> None:
        """Register a custom terminal launcher implementation."""
        cls._launcher_registry.insert(0, launcher_class)

    @classmethod
    def create(cls, config: Optional[TerminalConfig] = None) -> Optional[TerminalLauncher]:
        """Create a terminal launcher for the current platform.
        
        Returns None if no suitable terminal launcher is found.
        """
        effective_config = config or TerminalConfig.default()
        
        for launcher_class in cls._launcher_registry:
            launcher = launcher_class(effective_config)
            if launcher.is_available():
                return launcher
        
        return None

    @classmethod
    def create_or_raise(cls, config: Optional[TerminalConfig] = None) -> TerminalLauncher:
        """Create a terminal launcher or raise an exception if none is available."""
        launcher = cls.create(config)
        if launcher is None:
            raise TerminalNotFoundError(
                f"No suitable terminal emulator found for platform: {sys.platform}"
            )
        return launcher

    @classmethod
    def get_available_launchers(
        cls, config: Optional[TerminalConfig] = None
    ) -> List[TerminalLauncher]:
        """Get all available terminal launchers for the current platform."""
        effective_config = config or TerminalConfig.default()
        available = []
        
        for launcher_class in cls._launcher_registry:
            launcher = launcher_class(effective_config)
            if launcher.is_available():
                available.append(launcher)
        
        return available


class TerminalNotFoundError(Exception):
    """Raised when no suitable terminal emulator is found."""
    pass
