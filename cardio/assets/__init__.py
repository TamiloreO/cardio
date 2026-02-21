"""
Assets package for cardio UI components.

This module provides ASCII art generation capabilities for converting
images to ASCII art assets suitable for terminal/TUI display.

Usage:
    from cardio.assets import AsciiArtGenerator, image_to_ascii_art, generate_assets
    
    # Generate single image
    ascii_art = image_to_ascii_art("path/to/image.png", "output_name")
    
    # Use generator class for more control
    generator = AsciiArtGenerator(output_dir=Path("output"), width=60)
    ascii_art = generator.generate("path/to/image.png")
    
    # Generate all images from assets/images to assets/generated
    results = generate_assets(width=60, force=False)

Command-line usage:
    python -m cardio.assets.ascii_art_generator [--width WIDTH] [--force] [-v]
"""

from pathlib import Path

from .ascii_art_generator import (
    AsciiArtGenerator,
    AsciiArtGeneratorError,
    ImageNotFoundError,
    InvalidImageError,
    image_to_ascii_art,
    generate_assets,
    IMAGES_DIR,
    GENERATED_DIR,
)

ASSETS_DIR = Path(__file__).parent

__all__ = [
    "ASSETS_DIR",
    "IMAGES_DIR",
    "GENERATED_DIR",
    "AsciiArtGenerator",
    "AsciiArtGeneratorError",
    "ImageNotFoundError",
    "InvalidImageError",
    "image_to_ascii_art",
    "generate_assets",
]
