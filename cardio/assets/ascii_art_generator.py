"""
ASCII Art Generator Module

Provides functionality to convert images to ASCII art using pywhatkit-style algorithms.
Generated ASCII art files are stored in the assets directory for UI usage.
"""

import argparse
import hashlib
import json
import logging
import sys
from pathlib import Path
from typing import Optional, List, Dict

from PIL import Image

logger = logging.getLogger(__name__)


class AsciiArtGeneratorError(Exception):
    """Base exception for ASCII art generation errors."""
    pass


class ImageNotFoundError(AsciiArtGeneratorError):
    """Raised when the source image cannot be found."""
    pass


class InvalidImageError(AsciiArtGeneratorError):
    """Raised when the image cannot be processed."""
    pass


class AsciiArtGenerator:
    """
    Generator for converting images to ASCII art.
    
    Uses pywhatkit-style algorithm for image-to-ASCII conversion,
    producing text files suitable for terminal/TUI display.
    """
    
    DEFAULT_WIDTH = 80
    DEFAULT_ASPECT_RATIO_CORRECTION = 0.55
    DEFAULT_CHARS = ["*", "S", "#", "&", "@", "$", "%", "*", "!", ":", "."]
    CACHE_FILENAME = ".ascii_cache.json"
    
    def __init__(
        self,
        output_dir: Optional[Path] = None,
        width: int = DEFAULT_WIDTH,
        chars: Optional[List[str]] = None
    ):
        """
        Initialize the ASCII art generator.
        
        Args:
            output_dir: Directory for generated ASCII art files.
                       Defaults to the assets/generatedimages directory.
            width: Width of the output ASCII art in characters.
            chars: Character set for ASCII art rendering (dark to light).
        """
        if output_dir is None:
            output_dir = Path(__file__).parent / "generatedimages"
        self._output_dir = output_dir
        self._width = width
        self._chars = chars or self.DEFAULT_CHARS.copy()
        self._cache: Dict[str, str] = {}
        self._load_cache()
    
    @property
    def output_dir(self) -> Path:
        """Get the output directory for generated files."""
        return self._output_dir
    
    @property
    def width(self) -> int:
        """Get the configured ASCII art width."""
        return self._width
    
    @property
    def chars(self) -> List[str]:
        """Get the character set used for rendering."""
        return self._chars.copy()
    
    def _get_cache_path(self) -> Path:
        """Get the path to the cache file."""
        return self._output_dir / self.CACHE_FILENAME
    
    def _load_cache(self) -> None:
        """Load the cache from disk if it exists."""
        cache_path = self._get_cache_path()
        if cache_path.exists():
            try:
                self._cache = json.loads(cache_path.read_text())
            except (json.JSONDecodeError, OSError) as e:
                logger.warning("Failed to load cache file: %s", e)
                self._cache = {}
    
    def _save_cache(self) -> None:
        """Save the cache to disk."""
        cache_path = self._get_cache_path()
        try:
            self._output_dir.mkdir(parents=True, exist_ok=True)
            cache_path.write_text(json.dumps(self._cache, indent=2))
        except OSError as e:
            logger.warning("Failed to save cache file: %s", e)
    
    def _compute_file_hash(self, file_path: Path) -> str:
        """Compute MD5 hash of a file for cache invalidation."""
        hasher = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                hasher.update(chunk)
        hasher.update(str(self._width).encode())
        hasher.update("".join(self._chars).encode())
        return hasher.hexdigest()
    
    def _is_cached(self, image_path: Path) -> bool:
        """Check if an image has already been processed and cached."""
        output_name = image_path.stem
        output_path = self._output_dir / f"{output_name}.txt"
        
        if not output_path.exists():
            return False
        
        current_hash = self._compute_file_hash(image_path)
        cached_hash = self._cache.get(output_name)
        
        return current_hash == cached_hash
    
    def _update_cache(self, image_path: Path, output_name: str) -> None:
        """Update the cache with the processed image hash."""
        file_hash = self._compute_file_hash(image_path)
        self._cache[output_name] = file_hash
        self._save_cache()
    
    def generate(
        self,
        image_path: str,
        output_name: Optional[str] = None,
        width: Optional[int] = None,
        force: bool = False
    ) -> str:
        """
        Convert an image to ASCII art and save to file.
        
        Args:
            image_path: Path to the source image file.
            output_name: Name for the output file (without extension).
                        Defaults to the source image name.
            width: Override width for this generation.
            force: If True, regenerate even if cached.
        
        Returns:
            The generated ASCII art as a string.
        
        Raises:
            ImageNotFoundError: If the source image doesn't exist.
            InvalidImageError: If the image cannot be processed.
        """
        source_path = Path(image_path)
        if not source_path.exists():
            raise ImageNotFoundError(f"Image not found: {image_path}")
        
        output_filename = output_name or source_path.stem
        output_path = self._output_dir / f"{output_filename}.txt"
        
        if not force and self._is_cached(source_path):
            logger.info("Using cached ASCII art for: %s", source_path.name)
            return output_path.read_text()
        
        try:
            ascii_art = self._convert_image(source_path, width or self._width)
        except Exception as e:
            raise InvalidImageError(f"Failed to process image: {e}") from e
        
        self._output_dir.mkdir(parents=True, exist_ok=True)
        output_path.write_text(ascii_art)
        self._update_cache(source_path, output_filename)
        
        logger.info("Generated ASCII art for: %s -> %s", source_path.name, output_path.name)
        return ascii_art
    
    def _convert_image(self, image_path: Path, width: int) -> str:
        """
        Convert image to ASCII art string.
        
        This implementation follows the pywhatkit image_to_ascii_art algorithm.
        """
        img = Image.open(image_path).convert("L")
        
        original_width, original_height = img.size
        aspect_ratio = original_height / original_width
        new_height = int(aspect_ratio * width * self.DEFAULT_ASPECT_RATIO_CORRECTION)
        img = img.resize((width, new_height))
        
        pixels = list(img.getdata())
        
        char_count = len(self._chars)
        pixel_range = 256 // char_count
        new_pixels = [self._chars[min(pixel // pixel_range, char_count - 1)] for pixel in pixels]
        
        ascii_lines = []
        for i in range(0, len(new_pixels), width):
            ascii_lines.append("".join(new_pixels[i:i + width]))
        
        return "\n".join(ascii_lines)
    
    def generate_from_directory(
        self,
        source_dir: Optional[str] = None,
        extensions: Optional[List[str]] = None,
        force: bool = False
    ) -> dict:
        """
        Generate ASCII art for all images in a directory.
        
        Args:
            source_dir: Path to the directory containing images.
                       Defaults to assets/images directory.
            extensions: List of file extensions to process.
                       Defaults to ['.png', '.jpg', '.jpeg'].
            force: If True, regenerate all images even if cached.
        
        Returns:
            Dictionary mapping output filenames to generated ASCII art.
        
        Raises:
            FileNotFoundError: If the source directory doesn't exist.
        """
        if source_dir is None:
            source_path = Path(__file__).parent / "images"
        else:
            source_path = Path(source_dir)
        
        if not source_path.exists():
            raise FileNotFoundError(f"Directory not found: {source_path}")
        
        extensions = extensions or [".png", ".jpg", ".jpeg"]
        extensions = [ext.lower() for ext in extensions]
        
        results = {}
        for image_file in source_path.iterdir():
            if image_file.is_file() and image_file.suffix.lower() in extensions:
                try:
                    ascii_art = self.generate(str(image_file), force=force)
                    results[image_file.stem] = ascii_art
                except ImageNotFoundError as e:
                    logger.warning("Image not found, skipping: %s - %s", image_file.name, e)
                except InvalidImageError as e:
                    logger.warning("Invalid image, skipping: %s - %s", image_file.name, e)
                except AsciiArtGeneratorError as e:
                    logger.warning("Failed to process image: %s - %s", image_file.name, e)
        
        return results


def image_to_ascii_art(
    img_path: str,
    output_file: Optional[str] = None
) -> str:
    """
    Convert an image to ASCII art.
    
    This function provides a simple interface matching pywhatkit's
    image_to_ascii_art function signature.
    
    Args:
        img_path: Path to the source image.
        output_file: Name for output file (without extension).
                    Defaults to 'pywhatkit_asciiart'.
    
    Returns:
        The generated ASCII art as a string.
    """
    generator = AsciiArtGenerator()
    output_name = output_file or "pywhatkit_asciiart"
    return generator.generate(img_path, output_name)


def main() -> int:
    """Command-line interface for ASCII art generation."""
    parser = argparse.ArgumentParser(
        description="Convert images to ASCII art",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate ASCII art from a single image
  python -m cardio.assets.ascii_art_generator image.png

  # Generate with custom width
  python -m cardio.assets.ascii_art_generator image.png -w 60

  # Process all images in the default images directory
  python -m cardio.assets.ascii_art_generator --batch

  # Process all images in a custom directory
  python -m cardio.assets.ascii_art_generator --batch --source-dir ./my_images

  # Force regeneration of all images
  python -m cardio.assets.ascii_art_generator --batch --force
        """
    )
    
    parser.add_argument(
        "image",
        nargs="?",
        help="Path to the image file to convert"
    )
    parser.add_argument(
        "-o", "--output",
        help="Output filename (without extension)"
    )
    parser.add_argument(
        "-w", "--width",
        type=int,
        default=AsciiArtGenerator.DEFAULT_WIDTH,
        help=f"Width of ASCII art in characters (default: {AsciiArtGenerator.DEFAULT_WIDTH})"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Output directory for generated files"
    )
    parser.add_argument(
        "--batch",
        action="store_true",
        help="Process all images in source directory"
    )
    parser.add_argument(
        "--source-dir",
        type=Path,
        help="Source directory for batch processing (default: assets/images)"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force regeneration even if cached"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose output"
    )
    parser.add_argument(
        "--print",
        action="store_true",
        dest="print_output",
        help="Print ASCII art to stdout"
    )
    
    args = parser.parse_args()
    
    log_level = logging.INFO if args.verbose else logging.WARNING
    logging.basicConfig(
        level=log_level,
        format="%(levelname)s: %(message)s"
    )
    
    if not args.batch and not args.image:
        parser.error("Either provide an image path or use --batch for directory processing")
    
    try:
        generator = AsciiArtGenerator(
            output_dir=args.output_dir,
            width=args.width
        )
        
        if args.batch:
            source_dir = str(args.source_dir) if args.source_dir else None
            results = generator.generate_from_directory(
                source_dir=source_dir,
                force=args.force
            )
            print(f"Processed {len(results)} image(s)")
            for name in results:
                print(f"  - {name}.txt")
        else:
            ascii_art = generator.generate(
                args.image,
                output_name=args.output,
                force=args.force
            )
            if args.print_output:
                print(ascii_art)
            else:
                output_name = args.output or Path(args.image).stem
                print(f"Generated: {generator.output_dir / output_name}.txt")
        
        return 0
        
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except AsciiArtGeneratorError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
