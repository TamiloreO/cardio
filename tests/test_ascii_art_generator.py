"""Tests for the ASCII art generator module."""

import json
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from PIL import Image

from cardio.assets.ascii_art_generator import (
    AsciiArtGenerator,
    AsciiArtGeneratorError,
    ImageNotFoundError,
    InvalidImageError,
    image_to_ascii_art,
    main,
)
from cardio.assets import (
    AsciiArtGenerator as ExportedGenerator,
    image_to_ascii_art as exported_func,
    ASSETS_DIR,
    IMAGES_DIR,
    GENERATED_IMAGES_DIR,
)


class TestPackageExports:
    """Test that package exports are correctly configured."""

    def test_ascii_art_generator_exported(self):
        """Test AsciiArtGenerator is exported from package."""
        assert ExportedGenerator is AsciiArtGenerator

    def test_image_to_ascii_art_exported(self):
        """Test image_to_ascii_art is exported from package."""
        assert exported_func is image_to_ascii_art

    def test_assets_dir_exists(self):
        """Test ASSETS_DIR points to valid path."""
        assert ASSETS_DIR.exists()

    def test_images_dir_path(self):
        """Test IMAGES_DIR is correctly configured."""
        assert IMAGES_DIR == ASSETS_DIR / "images"

    def test_generated_images_dir_path(self):
        """Test GENERATED_IMAGES_DIR is correctly configured."""
        assert GENERATED_IMAGES_DIR == ASSETS_DIR / "generatedimages"


class TestAsciiArtGenerator:
    """Test suite for AsciiArtGenerator class."""

    def test_init_with_defaults(self, tmp_path):
        """Test generator initialization with default values."""
        generator = AsciiArtGenerator(output_dir=tmp_path)
        
        assert generator.output_dir == tmp_path
        assert generator.width == AsciiArtGenerator.DEFAULT_WIDTH
        assert generator.chars == AsciiArtGenerator.DEFAULT_CHARS

    def test_init_with_custom_values(self, tmp_path):
        """Test generator initialization with custom parameters."""
        custom_chars = ["@", "#", "*", "."]
        generator = AsciiArtGenerator(
            output_dir=tmp_path,
            width=40,
            chars=custom_chars
        )
        
        assert generator.width == 40
        assert generator.chars == custom_chars

    def test_chars_returns_copy(self, tmp_path):
        """Test that chars property returns a copy."""
        generator = AsciiArtGenerator(output_dir=tmp_path)
        chars = generator.chars
        chars.append("X")
        
        assert "X" not in generator.chars

    def test_generate_image_not_found(self, tmp_path):
        """Test that ImageNotFoundError is raised for missing images."""
        generator = AsciiArtGenerator(output_dir=tmp_path)
        
        with pytest.raises(ImageNotFoundError) as exc_info:
            generator.generate("/nonexistent/image.png")
        
        assert "Image not found" in str(exc_info.value)

    def test_generate_creates_output_file(self, tmp_path):
        """Test that generate creates the expected output file."""
        image_path = tmp_path / "test_image.png"
        img = Image.new("L", (10, 10), color=128)
        img.save(image_path)
        
        output_dir = tmp_path / "output"
        generator = AsciiArtGenerator(output_dir=output_dir, width=10)
        result = generator.generate(str(image_path))
        
        output_file = output_dir / "test_image.txt"
        assert output_file.exists()
        assert output_file.read_text() == result

    def test_generate_with_custom_output_name(self, tmp_path):
        """Test generate with custom output filename."""
        image_path = tmp_path / "source.png"
        img = Image.new("L", (10, 10), color=128)
        img.save(image_path)
        
        output_dir = tmp_path / "output"
        generator = AsciiArtGenerator(output_dir=output_dir, width=10)
        generator.generate(str(image_path), output_name="custom_output")
        
        assert (output_dir / "custom_output.txt").exists()
        assert not (output_dir / "source.txt").exists()

    def test_generate_with_width_override(self, tmp_path):
        """Test generate with width override."""
        image_path = tmp_path / "test.png"
        img = Image.new("L", (100, 100), color=128)
        img.save(image_path)
        
        output_dir = tmp_path / "output"
        generator = AsciiArtGenerator(output_dir=output_dir, width=80)
        result = generator.generate(str(image_path), width=20)
        
        lines = result.split("\n")
        assert all(len(line) == 20 for line in lines)

    def test_generate_grayscale_conversion(self, tmp_path):
        """Test that colored images are converted to grayscale."""
        image_path = tmp_path / "color.png"
        img = Image.new("RGB", (10, 10), color=(255, 0, 0))
        img.save(image_path)
        
        output_dir = tmp_path / "output"
        generator = AsciiArtGenerator(output_dir=output_dir, width=10)
        result = generator.generate(str(image_path))
        
        assert isinstance(result, str)
        assert len(result) > 0

    def test_generate_preserves_aspect_ratio(self, tmp_path):
        """Test that aspect ratio is preserved in output."""
        image_path = tmp_path / "wide.png"
        img = Image.new("L", (100, 50), color=128)
        img.save(image_path)
        
        output_dir = tmp_path / "output"
        generator = AsciiArtGenerator(output_dir=output_dir, width=40)
        result = generator.generate(str(image_path))
        
        lines = result.split("\n")
        expected_height = int(0.5 * 40 * 0.55)
        assert abs(len(lines) - expected_height) <= 1

    def test_generate_dark_pixels_use_dense_chars(self, tmp_path):
        """Test that dark pixels map to dense characters."""
        image_path = tmp_path / "dark.png"
        img = Image.new("L", (10, 10), color=0)
        img.save(image_path)
        
        output_dir = tmp_path / "output"
        generator = AsciiArtGenerator(output_dir=output_dir, width=10)
        result = generator.generate(str(image_path))
        
        assert generator.chars[0] in result

    def test_generate_light_pixels_use_sparse_chars(self, tmp_path):
        """Test that light pixels map to sparse characters."""
        image_path = tmp_path / "light.png"
        img = Image.new("L", (10, 10), color=255)
        img.save(image_path)
        
        output_dir = tmp_path / "output"
        generator = AsciiArtGenerator(output_dir=output_dir, width=10)
        result = generator.generate(str(image_path))
        
        assert generator.chars[-1] in result

    def test_generate_creates_output_dir(self, tmp_path):
        """Test that output directory is created if it doesn't exist."""
        nested_dir = tmp_path / "nested" / "output"
        image_path = tmp_path / "test.png"
        img = Image.new("L", (10, 10), color=128)
        img.save(image_path)
        
        generator = AsciiArtGenerator(output_dir=nested_dir, width=10)
        generator.generate(str(image_path))
        
        assert nested_dir.exists()

    def test_generate_invalid_image_raises_error(self, tmp_path):
        """Test that invalid images raise InvalidImageError."""
        invalid_file = tmp_path / "not_an_image.png"
        invalid_file.write_text("not image data")
        
        output_dir = tmp_path / "output"
        generator = AsciiArtGenerator(output_dir=output_dir)
        
        with pytest.raises(InvalidImageError) as exc_info:
            generator.generate(str(invalid_file))
        
        assert "Failed to process image" in str(exc_info.value)


class TestCaching:
    """Test suite for caching functionality."""

    def test_caching_skips_regeneration(self, tmp_path):
        """Test that cached images are not regenerated."""
        image_path = tmp_path / "test.png"
        img = Image.new("L", (10, 10), color=128)
        img.save(image_path)
        
        output_dir = tmp_path / "output"
        generator = AsciiArtGenerator(output_dir=output_dir, width=10)
        
        result1 = generator.generate(str(image_path))
        result2 = generator.generate(str(image_path))
        
        assert result1 == result2

    def test_cache_file_created(self, tmp_path):
        """Test that cache file is created after generation."""
        image_path = tmp_path / "test.png"
        img = Image.new("L", (10, 10), color=128)
        img.save(image_path)
        
        output_dir = tmp_path / "output"
        generator = AsciiArtGenerator(output_dir=output_dir, width=10)
        generator.generate(str(image_path))
        
        cache_file = output_dir / AsciiArtGenerator.CACHE_FILENAME
        assert cache_file.exists()

    def test_cache_contains_file_hash(self, tmp_path):
        """Test that cache contains hash for processed image."""
        image_path = tmp_path / "test.png"
        img = Image.new("L", (10, 10), color=128)
        img.save(image_path)
        
        output_dir = tmp_path / "output"
        generator = AsciiArtGenerator(output_dir=output_dir, width=10)
        generator.generate(str(image_path))
        
        cache_file = output_dir / AsciiArtGenerator.CACHE_FILENAME
        cache_data = json.loads(cache_file.read_text())
        
        assert "test" in cache_data
        assert isinstance(cache_data["test"], str)

    def test_force_regeneration_ignores_cache(self, tmp_path):
        """Test that force=True regenerates even if cached."""
        image_path = tmp_path / "test.png"
        img = Image.new("L", (10, 10), color=128)
        img.save(image_path)
        
        output_dir = tmp_path / "output"
        generator = AsciiArtGenerator(output_dir=output_dir, width=10)
        
        generator.generate(str(image_path))
        
        output_file = output_dir / "test.txt"
        original_mtime = output_file.stat().st_mtime
        
        import time
        time.sleep(0.1)
        
        generator.generate(str(image_path), force=True)
        new_mtime = output_file.stat().st_mtime
        
        assert new_mtime > original_mtime

    def test_cache_invalidation_on_image_change(self, tmp_path):
        """Test that cache is invalidated when image changes."""
        image_path = tmp_path / "test.png"
        img = Image.new("L", (10, 10), color=128)
        img.save(image_path)
        
        output_dir = tmp_path / "output"
        generator = AsciiArtGenerator(output_dir=output_dir, width=10)
        
        result1 = generator.generate(str(image_path))
        
        img2 = Image.new("L", (10, 10), color=0)
        img2.save(image_path)
        
        generator2 = AsciiArtGenerator(output_dir=output_dir, width=10)
        result2 = generator2.generate(str(image_path))
        
        assert result1 != result2

    def test_cache_loaded_on_init(self, tmp_path):
        """Test that cache is loaded when generator is initialized."""
        image_path = tmp_path / "test.png"
        img = Image.new("L", (10, 10), color=128)
        img.save(image_path)
        
        output_dir = tmp_path / "output"
        generator1 = AsciiArtGenerator(output_dir=output_dir, width=10)
        generator1.generate(str(image_path))
        
        generator2 = AsciiArtGenerator(output_dir=output_dir, width=10)
        
        assert generator2._is_cached(image_path)


class TestGenerateFromDirectory:
    """Test suite for generate_from_directory method."""

    def test_generate_from_directory_processes_images(self, tmp_path):
        """Test that all images in directory are processed."""
        source_dir = tmp_path / "source"
        source_dir.mkdir()
        
        for name in ["img1.png", "img2.jpg", "img3.jpeg"]:
            img = Image.new("L", (10, 10), color=128)
            img.save(source_dir / name)
        
        output_dir = tmp_path / "output"
        generator = AsciiArtGenerator(output_dir=output_dir, width=10)
        results = generator.generate_from_directory(str(source_dir))
        
        assert len(results) == 3
        assert "img1" in results
        assert "img2" in results
        assert "img3" in results

    def test_generate_from_directory_skips_non_images(self, tmp_path):
        """Test that non-image files are skipped."""
        source_dir = tmp_path / "source"
        source_dir.mkdir()
        
        img = Image.new("L", (10, 10), color=128)
        img.save(source_dir / "valid.png")
        (source_dir / "readme.txt").write_text("not an image")
        
        output_dir = tmp_path / "output"
        generator = AsciiArtGenerator(output_dir=output_dir, width=10)
        results = generator.generate_from_directory(str(source_dir))
        
        assert len(results) == 1
        assert "valid" in results

    def test_generate_from_directory_custom_extensions(self, tmp_path):
        """Test filtering by custom extensions."""
        source_dir = tmp_path / "source"
        source_dir.mkdir()
        
        for name in ["img.png", "img.bmp"]:
            img = Image.new("L", (10, 10), color=128)
            img.save(source_dir / name)
        
        output_dir = tmp_path / "output"
        generator = AsciiArtGenerator(output_dir=output_dir, width=10)
        results = generator.generate_from_directory(
            str(source_dir),
            extensions=[".bmp"]
        )
        
        assert len(results) == 1
        assert "img" in results

    def test_generate_from_directory_not_found(self, tmp_path):
        """Test that missing directory raises FileNotFoundError."""
        generator = AsciiArtGenerator(output_dir=tmp_path)
        
        with pytest.raises(FileNotFoundError):
            generator.generate_from_directory("/nonexistent/directory")

    def test_generate_from_directory_logs_invalid_images(self, tmp_path, caplog):
        """Test that invalid images are logged as warnings."""
        import logging
        
        source_dir = tmp_path / "source"
        source_dir.mkdir()
        
        img = Image.new("L", (10, 10), color=128)
        img.save(source_dir / "valid.png")
        (source_dir / "invalid.png").write_text("not image data")
        
        output_dir = tmp_path / "output"
        generator = AsciiArtGenerator(output_dir=output_dir, width=10)
        
        with caplog.at_level(logging.WARNING):
            results = generator.generate_from_directory(str(source_dir))
        
        assert len(results) == 1
        assert "valid" in results
        assert any("invalid.png" in record.message for record in caplog.records)

    def test_generate_from_directory_case_insensitive_extensions(self, tmp_path):
        """Test that extension matching is case-insensitive."""
        source_dir = tmp_path / "source"
        source_dir.mkdir()
        
        img = Image.new("L", (10, 10), color=128)
        img.save(source_dir / "upper.PNG")
        
        output_dir = tmp_path / "output"
        generator = AsciiArtGenerator(output_dir=output_dir, width=10)
        results = generator.generate_from_directory(str(source_dir))
        
        assert len(results) == 1

    def test_generate_from_directory_with_force(self, tmp_path):
        """Test force regeneration in batch mode."""
        source_dir = tmp_path / "source"
        source_dir.mkdir()
        
        img = Image.new("L", (10, 10), color=128)
        img.save(source_dir / "test.png")
        
        output_dir = tmp_path / "output"
        generator = AsciiArtGenerator(output_dir=output_dir, width=10)
        
        generator.generate_from_directory(str(source_dir))
        output_file = output_dir / "test.txt"
        original_mtime = output_file.stat().st_mtime
        
        import time
        time.sleep(0.1)
        
        generator.generate_from_directory(str(source_dir), force=True)
        new_mtime = output_file.stat().st_mtime
        
        assert new_mtime > original_mtime


class TestImageToAsciiArtFunction:
    """Test suite for the standalone image_to_ascii_art function."""

    def test_image_to_ascii_art_basic(self, tmp_path, monkeypatch):
        """Test basic functionality of image_to_ascii_art."""
        monkeypatch.chdir(tmp_path)
        
        image_path = tmp_path / "test.png"
        img = Image.new("L", (10, 10), color=128)
        img.save(image_path)
        
        with patch("cardio.assets.ascii_art_generator.AsciiArtGenerator") as MockGenerator:
            mock_instance = Mock()
            mock_instance.generate.return_value = "ASCII ART"
            MockGenerator.return_value = mock_instance
            
            result = image_to_ascii_art(str(image_path))
            
            mock_instance.generate.assert_called_once_with(
                str(image_path),
                "pywhatkit_asciiart"
            )
            assert result == "ASCII ART"

    def test_image_to_ascii_art_custom_output(self, tmp_path, monkeypatch):
        """Test image_to_ascii_art with custom output name."""
        monkeypatch.chdir(tmp_path)
        
        image_path = tmp_path / "test.png"
        img = Image.new("L", (10, 10), color=128)
        img.save(image_path)
        
        with patch("cardio.assets.ascii_art_generator.AsciiArtGenerator") as MockGenerator:
            mock_instance = Mock()
            mock_instance.generate.return_value = "ASCII ART"
            MockGenerator.return_value = mock_instance
            
            image_to_ascii_art(str(image_path), output_file="custom")
            
            mock_instance.generate.assert_called_once_with(
                str(image_path),
                "custom"
            )


class TestExceptionHierarchy:
    """Test suite for exception class hierarchy."""

    def test_image_not_found_is_generator_error(self):
        """Test ImageNotFoundError inherits from AsciiArtGeneratorError."""
        assert issubclass(ImageNotFoundError, AsciiArtGeneratorError)

    def test_invalid_image_is_generator_error(self):
        """Test InvalidImageError inherits from AsciiArtGeneratorError."""
        assert issubclass(InvalidImageError, AsciiArtGeneratorError)

    def test_generator_error_is_exception(self):
        """Test AsciiArtGeneratorError inherits from Exception."""
        assert issubclass(AsciiArtGeneratorError, Exception)


class TestCommandLineInterface:
    """Test suite for the command-line interface."""

    def test_cli_single_image(self, tmp_path, monkeypatch):
        """Test CLI with single image argument."""
        image_path = tmp_path / "test.png"
        img = Image.new("L", (10, 10), color=128)
        img.save(image_path)
        
        output_dir = tmp_path / "output"
        
        monkeypatch.setattr(
            "sys.argv",
            ["prog", str(image_path), "--output-dir", str(output_dir), "-w", "10"]
        )
        
        result = main()
        
        assert result == 0
        assert (output_dir / "test.txt").exists()

    def test_cli_batch_mode(self, tmp_path, monkeypatch):
        """Test CLI batch mode."""
        source_dir = tmp_path / "source"
        source_dir.mkdir()
        
        img = Image.new("L", (10, 10), color=128)
        img.save(source_dir / "test.png")
        
        output_dir = tmp_path / "output"
        
        monkeypatch.setattr(
            "sys.argv",
            ["prog", "--batch", "--source-dir", str(source_dir), "--output-dir", str(output_dir), "-w", "10"]
        )
        
        result = main()
        
        assert result == 0
        assert (output_dir / "test.txt").exists()

    def test_cli_missing_image_error(self, tmp_path, monkeypatch):
        """Test CLI returns error for missing image."""
        monkeypatch.setattr(
            "sys.argv",
            ["prog", "/nonexistent/image.png", "--output-dir", str(tmp_path)]
        )
        
        result = main()
        
        assert result == 1

    def test_cli_print_option(self, tmp_path, monkeypatch, capsys):
        """Test CLI --print option outputs to stdout."""
        image_path = tmp_path / "test.png"
        img = Image.new("L", (10, 10), color=128)
        img.save(image_path)
        
        output_dir = tmp_path / "output"
        
        monkeypatch.setattr(
            "sys.argv",
            ["prog", str(image_path), "--output-dir", str(output_dir), "-w", "10", "--print"]
        )
        
        result = main()
        captured = capsys.readouterr()
        
        assert result == 0
        assert len(captured.out.strip()) > 0

    def test_cli_force_option(self, tmp_path, monkeypatch):
        """Test CLI --force option."""
        image_path = tmp_path / "test.png"
        img = Image.new("L", (10, 10), color=128)
        img.save(image_path)
        
        output_dir = tmp_path / "output"
        generator = AsciiArtGenerator(output_dir=output_dir, width=10)
        generator.generate(str(image_path))
        
        output_file = output_dir / "test.txt"
        original_mtime = output_file.stat().st_mtime
        
        import time
        time.sleep(0.1)
        
        monkeypatch.setattr(
            "sys.argv",
            ["prog", str(image_path), "--output-dir", str(output_dir), "-w", "10", "--force"]
        )
        
        result = main()
        new_mtime = output_file.stat().st_mtime
        
        assert result == 0
        assert new_mtime > original_mtime

    def test_cli_no_args_error(self, monkeypatch, capsys):
        """Test CLI returns error when no arguments provided."""
        monkeypatch.setattr("sys.argv", ["prog"])
        
        with pytest.raises(SystemExit) as exc_info:
            main()
        
        assert exc_info.value.code == 2
