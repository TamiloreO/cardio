"""ASCII art generation utilities using pywhatkit.

This module wraps pywhatkit's image_to_ascii_art functionality to generate
ASCII art assets for the cardio game UI. Generated assets are stored in the
assets directory and can be loaded for display in the TUI.

The pywhatkit.ascii_art module is imported directly rather than through pywhatkit's
__init__.py to avoid triggering pyautogui's display requirement on headless systems.
"""

from pathlib import Path
from typing import Optional, Tuple
import importlib.util
import sys

ASSETS_DIR = Path(__file__).resolve().parent
DEFAULT_WIDTH = 80

_pywhatkit_ascii_art = None


def _get_pywhatkit_converter():
    """Import pywhatkit's ascii_art function directly to avoid display-related errors.

    pywhatkit's __init__.py imports pyautogui which requires a display connection.
    By importing the ascii_art module directly via importlib from its file path,
    we bypass this issue for headless environments.
    """
    global _pywhatkit_ascii_art

    if _pywhatkit_ascii_art is not None:
        return _pywhatkit_ascii_art

    # Find pywhatkit's installation directory without importing it
    for path in sys.path:
        ascii_art_path = Path(path) / "pywhatkit" / "ascii_art.py"
        if ascii_art_path.exists():
            spec = importlib.util.spec_from_file_location(
                "pywhatkit_ascii_art", ascii_art_path
            )
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                _pywhatkit_ascii_art = module.image_to_ascii_art
                return _pywhatkit_ascii_art

    raise ImportError(
        "Could not find pywhatkit.ascii_art module. "
        "Please ensure pywhatkit is installed: pip install pywhatkit"
    )


def get_asset_path(name: str) -> Path:
    """Get the path to an ASCII art asset file.

    Args:
        name: Asset name (without .txt extension).

    Returns:
        Path to the asset file.
    """
    return ASSETS_DIR / f"{name}.txt"


def image_to_ascii(
    image_path: str,
    output_name: Optional[str] = None,
    width: int = DEFAULT_WIDTH,
    chars: Optional[str] = None,
) -> str:
    """Convert an image to ASCII art.

    This is a wrapper around pywhatkit's image_to_ascii_art that provides
    additional customization options for width and character set.

    Args:
        image_path: Path to the source image file.
        output_name: Name for the output file (without extension).
            If None, uses the image filename.
        width: Width of the ASCII art in characters. Defaults to 80.
        chars: Custom character set for ASCII conversion (darkest to lightest).
            If None, uses pywhatkit's default.

    Returns:
        The generated ASCII art as a string.
    """
    from PIL import Image

    if output_name is None:
        output_name = Path(image_path).stem

    output_path = ASSETS_DIR / output_name

    img = Image.open(image_path).convert("L")

    original_width, original_height = img.size
    aspect_ratio = original_height / original_width
    new_height = int(aspect_ratio * width * 0.55)
    img = img.resize((width, new_height))

    pixels = img.getdata()

    char_set = chars if chars else "*S#&@$%*!:."
    num_chars = len(char_set)
    char_map = [char_set[pixel * num_chars // 256] for pixel in pixels]
    ascii_str = "".join(char_map)

    ascii_lines = [
        ascii_str[i : i + width] for i in range(0, len(ascii_str), width)
    ]
    ascii_art = "\n".join(ascii_lines)

    output_file = f"{output_path}.txt"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(ascii_art)

    return ascii_art


def generate_asset(
    image_path: str,
    asset_name: str,
    size: Optional[Tuple[int, int]] = None,
) -> Path:
    """Generate an ASCII art asset from an image using pywhatkit.

    This uses pywhatkit's native image_to_ascii_art function directly.

    Args:
        image_path: Path to the source image file.
        asset_name: Name for the generated asset (without .txt extension).
        size: Optional tuple of (width, height) to resize before conversion.
            If None, uses pywhatkit's default sizing.

    Returns:
        Path to the generated asset file.

    Raises:
        FileNotFoundError: If the source image doesn't exist.
        ValueError: If the image format is not supported.
    """
    source = Path(image_path)
    if not source.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")

    if source.suffix.lower() not in {".png", ".jpg", ".jpeg", ".gif", ".bmp"}:
        raise ValueError(f"Unsupported image format: {source.suffix}")

    output_path = str(ASSETS_DIR / asset_name)

    image_to_ascii_art = _get_pywhatkit_converter()

    if size:
        from PIL import Image

        img = Image.open(image_path)
        img = img.resize(size)
        temp_path = ASSETS_DIR / f"_temp_{asset_name}{source.suffix}"
        img.save(temp_path)
        image_to_ascii_art(str(temp_path), output_path)
        temp_path.unlink()
    else:
        image_to_ascii_art(str(source), output_path)

    return get_asset_path(asset_name)


def load_asset(name: str) -> str:
    """Load an ASCII art asset from file.

    Args:
        name: Asset name (without .txt extension).

    Returns:
        The ASCII art content as a string.

    Raises:
        FileNotFoundError: If the asset doesn't exist.
    """
    asset_path = get_asset_path(name)
    if not asset_path.exists():
        raise FileNotFoundError(f"Asset not found: {name}")

    with open(asset_path, "r", encoding="utf-8") as f:
        return f.read()
