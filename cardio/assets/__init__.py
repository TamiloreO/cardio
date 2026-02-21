"""
Assets package for cardio UI components.

This module provides ASCII art generation capabilities using pywhatkit-style
algorithms for converting images to ASCII art assets.
"""

from pathlib import Path

from .ascii_art_generator import (
    AsciiArtGenerator,
    AsciiArtGeneratorError,
    ImageNotFoundError,
    InvalidImageError,
    image_to_ascii_art,
)

ASSETS_DIR = Path(__file__).parent
IMAGES_DIR = ASSETS_DIR / "images"
GENERATED_IMAGES_DIR = ASSETS_DIR / "generatedimages"

__all__ = [
    "AsciiArtGenerator",
    "AsciiArtGeneratorError",
    "ImageNotFoundError",
    "InvalidImageError",
    "image_to_ascii_art",
    "ASSETS_DIR",
    "IMAGES_DIR",
    "GENERATED_IMAGES_DIR",
]
