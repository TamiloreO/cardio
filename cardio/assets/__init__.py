"""ASCII art asset generation and management for the cardio TUI.

This module provides utilities for converting images to ASCII art using pywhatkit,
which can be used to generate visual assets for the game's text-based UI.
"""

from .ascii_art_generator import (
    image_to_ascii,
    generate_asset,
    get_asset_path,
    load_asset,
    ASSETS_DIR,
)

__all__ = [
    "image_to_ascii",
    "generate_asset",
    "get_asset_path",
    "load_asset",
    "ASSETS_DIR",
]
