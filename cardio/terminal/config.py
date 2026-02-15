from dataclasses import dataclass
from typing import Optional


@dataclass
class TerminalDimensions:
    """Represents terminal window dimensions."""
    width: int
    height: int

    @classmethod
    def maximized(cls) -> "TerminalDimensions":
        return cls(width=-1, height=-1)

    def is_maximized(self) -> bool:
        return self.width == -1 and self.height == -1


@dataclass
class TerminalConfig:
    """Configuration for terminal launching."""
    dimensions: TerminalDimensions
    title: Optional[str] = None
    working_directory: Optional[str] = None
    unicode_support: bool = True
    
    @classmethod
    def default(cls) -> "TerminalConfig":
        return cls(
            dimensions=TerminalDimensions.maximized(),
            title="Cardio",
            unicode_support=True,
        )
