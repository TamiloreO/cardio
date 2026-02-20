"""
ASCII Art Generator Module

Provides functionality to convert images to ASCII art using pywhatkit.
Generated ASCII art files are stored in the assets directory for UI usage.
"""

from pathlib import Path
from typing import Optional, List

from PIL import Image


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
                       Defaults to the assets directory.
            width: Width of the output ASCII art in characters.
            chars: Character set for ASCII art rendering (dark to light).
        """
        self._output_dir = output_dir or Path(__file__).parent
        self._width = width
        self._chars = chars or self.DEFAULT_CHARS.copy()
    
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
    
    def generate(
        self,
        image_path: str,
        output_name: Optional[str] = None,
        width: Optional[int] = None
    ) -> str:
        """
        Convert an image to ASCII art and save to file.
        
        Args:
            image_path: Path to the source image file.
            output_name: Name for the output file (without extension).
                        Defaults to the source image name.
            width: Override width for this generation.
        
        Returns:
            The generated ASCII art as a string.
        
        Raises:
            ImageNotFoundError: If the source image doesn't exist.
            InvalidImageError: If the image cannot be processed.
        """
        source_path = Path(image_path)
        if not source_path.exists():
            raise ImageNotFoundError(f"Image not found: {image_path}")
        
        try:
            ascii_art = self._convert_image(source_path, width or self._width)
        except Exception as e:
            raise InvalidImageError(f"Failed to process image: {e}") from e
        
        output_filename = output_name or source_path.stem
        output_path = self._output_dir / f"{output_filename}.txt"
        
        self._output_dir.mkdir(parents=True, exist_ok=True)
        output_path.write_text(ascii_art)
        
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
        source_dir: str,
        extensions: Optional[List[str]] = None
    ) -> dict:
        """
        Generate ASCII art for all images in a directory.
        
        Args:
            source_dir: Path to the directory containing images.
            extensions: List of file extensions to process.
                       Defaults to ['.png', '.jpg', '.jpeg'].
        
        Returns:
            Dictionary mapping output filenames to generated ASCII art.
        
        Raises:
            FileNotFoundError: If the source directory doesn't exist.
        """
        source_path = Path(source_dir)
        if not source_path.exists():
            raise FileNotFoundError(f"Directory not found: {source_dir}")
        
        extensions = extensions or [".png", ".jpg", ".jpeg"]
        extensions = [ext.lower() for ext in extensions]
        
        results = {}
        for image_file in source_path.iterdir():
            if image_file.is_file() and image_file.suffix.lower() in extensions:
                try:
                    ascii_art = self.generate(str(image_file))
                    results[image_file.stem] = ascii_art
                except AsciiArtGeneratorError:
                    continue
        
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
