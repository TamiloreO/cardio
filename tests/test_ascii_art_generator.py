"""Tests for the ASCII art generator module."""

import json
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from PIL import Image

from cardio.assets import (
    AsciiArtGenerator,
    AsciiArtGeneratorError,
    ImageNotFoundError,
    InvalidImageError,
    image_to_ascii_art,
    generate_assets,
    ASSETS_DIR,
    IMAGES_DIR,
    GENERATED_DIR,
)


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
        
        generator = AsciiArtGenerator(output_dir=tmp_path, width=10)
        result = generator.generate(str(image_path))
        
        output_file = tmp_path / "test_image.txt"
        assert output_file.exists()
        assert output_file.read_text() == result

    def test_generate_with_custom_output_name(self, tmp_path):
        """Test generate with custom output filename."""
        image_path = tmp_path / "source.png"
        img = Image.new("L", (10, 10), color=128)
        img.save(image_path)
        
        generator = AsciiArtGenerator(output_dir=tmp_path, width=10)
        generator.generate(str(image_path), output_name="custom_output")
        
        assert (tmp_path / "custom_output.txt").exists()
        assert not (tmp_path / "source.txt").exists()

    def test_generate_with_width_override(self, tmp_path):
        """Test generate with width override."""
        image_path = tmp_path / "test.png"
        img = Image.new("L", (100, 100), color=128)
        img.save(image_path)
        
        generator = AsciiArtGenerator(output_dir=tmp_path, width=80)
        result = generator.generate(str(image_path), width=20)
        
        lines = result.split("\n")
        assert all(len(line) == 20 for line in lines)

    def test_generate_grayscale_conversion(self, tmp_path):
        """Test that colored images are converted to grayscale."""
        image_path = tmp_path / "color.png"
        img = Image.new("RGB", (10, 10), color=(255, 0, 0))
        img.save(image_path)
        
        generator = AsciiArtGenerator(output_dir=tmp_path, width=10)
        result = generator.generate(str(image_path))
        
        assert isinstance(result, str)
        assert len(result) > 0

    def test_generate_preserves_aspect_ratio(self, tmp_path):
        """Test that aspect ratio is preserved in output."""
        image_path = tmp_path / "wide.png"
        img = Image.new("L", (100, 50), color=128)
        img.save(image_path)
        
        generator = AsciiArtGenerator(output_dir=tmp_path, width=40)
        result = generator.generate(str(image_path))
        
        lines = result.split("\n")
        # Height should be roughly half of width adjusted for aspect correction
        expected_height = int(0.5 * 40 * 0.55)
        assert abs(len(lines) - expected_height) <= 1

    def test_generate_dark_pixels_use_dense_chars(self, tmp_path):
        """Test that dark pixels map to dense characters."""
        image_path = tmp_path / "dark.png"
        img = Image.new("L", (10, 10), color=0)  # Black image
        img.save(image_path)
        
        generator = AsciiArtGenerator(output_dir=tmp_path, width=10)
        result = generator.generate(str(image_path))
        
        # First character in default set is for darkest pixels
        assert generator.chars[0] in result

    def test_generate_light_pixels_use_sparse_chars(self, tmp_path):
        """Test that light pixels map to sparse characters."""
        image_path = tmp_path / "light.png"
        img = Image.new("L", (10, 10), color=255)  # White image
        img.save(image_path)
        
        generator = AsciiArtGenerator(output_dir=tmp_path, width=10)
        result = generator.generate(str(image_path))
        
        # Last character in default set is for lightest pixels
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
        
        generator = AsciiArtGenerator(output_dir=tmp_path)
        
        with pytest.raises(InvalidImageError) as exc_info:
            generator.generate(str(invalid_file))
        
        assert "Failed to process image" in str(exc_info.value)


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


class TestGenerateAssets:
    """Test suite for generate_assets function with caching."""

    def test_generate_assets_creates_directories(self, tmp_path, monkeypatch):
        """Test that generate_assets creates required directories."""
        images_dir = tmp_path / "images"
        generated_dir = tmp_path / "generated"
        
        monkeypatch.setattr(
            "cardio.assets.ascii_art_generator.IMAGES_DIR", images_dir
        )
        monkeypatch.setattr(
            "cardio.assets.ascii_art_generator.GENERATED_DIR", generated_dir
        )
        monkeypatch.setattr(
            "cardio.assets.ascii_art_generator.CACHE_FILE",
            generated_dir / ".cache.json"
        )
        
        generate_assets()
        
        assert images_dir.exists()
        assert generated_dir.exists()

    def test_generate_assets_processes_images(self, tmp_path, monkeypatch):
        """Test that generate_assets processes all images."""
        images_dir = tmp_path / "images"
        generated_dir = tmp_path / "generated"
        images_dir.mkdir()
        
        for name in ["img1.png", "img2.jpg"]:
            img = Image.new("L", (10, 10), color=128)
            img.save(images_dir / name)
        
        monkeypatch.setattr(
            "cardio.assets.ascii_art_generator.IMAGES_DIR", images_dir
        )
        monkeypatch.setattr(
            "cardio.assets.ascii_art_generator.GENERATED_DIR", generated_dir
        )
        monkeypatch.setattr(
            "cardio.assets.ascii_art_generator.CACHE_FILE",
            generated_dir / ".cache.json"
        )
        
        results = generate_assets(width=10)
        
        assert len(results) == 2
        assert (generated_dir / "img1.txt").exists()
        assert (generated_dir / "img2.txt").exists()

    def test_generate_assets_uses_cache(self, tmp_path, monkeypatch):
        """Test that generate_assets skips cached images."""
        images_dir = tmp_path / "images"
        generated_dir = tmp_path / "generated"
        images_dir.mkdir()
        generated_dir.mkdir()
        
        img = Image.new("L", (10, 10), color=128)
        img.save(images_dir / "cached.png")
        
        monkeypatch.setattr(
            "cardio.assets.ascii_art_generator.IMAGES_DIR", images_dir
        )
        monkeypatch.setattr(
            "cardio.assets.ascii_art_generator.GENERATED_DIR", generated_dir
        )
        monkeypatch.setattr(
            "cardio.assets.ascii_art_generator.CACHE_FILE",
            generated_dir / ".cache.json"
        )
        
        # First run - should generate
        results1 = generate_assets(width=10)
        assert len(results1) == 1
        
        # Modify the output file to detect if it gets regenerated
        output_file = generated_dir / "cached.txt"
        original_content = output_file.read_text()
        output_file.write_text("MODIFIED")
        
        # Second run - should use cache and NOT regenerate
        results2 = generate_assets(width=10)
        assert len(results2) == 1
        assert output_file.read_text() == "MODIFIED"

    def test_generate_assets_force_regenerates(self, tmp_path, monkeypatch):
        """Test that force=True ignores cache."""
        images_dir = tmp_path / "images"
        generated_dir = tmp_path / "generated"
        images_dir.mkdir()
        generated_dir.mkdir()
        
        img = Image.new("L", (10, 10), color=128)
        img.save(images_dir / "test.png")
        
        monkeypatch.setattr(
            "cardio.assets.ascii_art_generator.IMAGES_DIR", images_dir
        )
        monkeypatch.setattr(
            "cardio.assets.ascii_art_generator.GENERATED_DIR", generated_dir
        )
        monkeypatch.setattr(
            "cardio.assets.ascii_art_generator.CACHE_FILE",
            generated_dir / ".cache.json"
        )
        
        # First run
        generate_assets(width=10)
        
        # Modify output
        output_file = generated_dir / "test.txt"
        output_file.write_text("MODIFIED")
        
        # Force regenerate
        generate_assets(width=10, force=True)
        assert output_file.read_text() != "MODIFIED"

    def test_generate_assets_regenerates_on_width_change(self, tmp_path, monkeypatch):
        """Test that changing width triggers regeneration."""
        images_dir = tmp_path / "images"
        generated_dir = tmp_path / "generated"
        images_dir.mkdir()
        generated_dir.mkdir()
        
        img = Image.new("L", (20, 20), color=128)
        img.save(images_dir / "test.png")
        
        monkeypatch.setattr(
            "cardio.assets.ascii_art_generator.IMAGES_DIR", images_dir
        )
        monkeypatch.setattr(
            "cardio.assets.ascii_art_generator.GENERATED_DIR", generated_dir
        )
        monkeypatch.setattr(
            "cardio.assets.ascii_art_generator.CACHE_FILE",
            generated_dir / ".cache.json"
        )
        
        # First run with width=10
        results1 = generate_assets(width=10)
        content1 = (generated_dir / "test.txt").read_text()
        
        # Second run with width=20 - should regenerate
        results2 = generate_assets(width=20)
        content2 = (generated_dir / "test.txt").read_text()
        
        assert content1 != content2

    def test_generate_assets_regenerates_on_image_change(self, tmp_path, monkeypatch):
        """Test that modifying image triggers regeneration."""
        images_dir = tmp_path / "images"
        generated_dir = tmp_path / "generated"
        images_dir.mkdir()
        generated_dir.mkdir()
        
        monkeypatch.setattr(
            "cardio.assets.ascii_art_generator.IMAGES_DIR", images_dir
        )
        monkeypatch.setattr(
            "cardio.assets.ascii_art_generator.GENERATED_DIR", generated_dir
        )
        monkeypatch.setattr(
            "cardio.assets.ascii_art_generator.CACHE_FILE",
            generated_dir / ".cache.json"
        )
        
        # Create and process first image
        img1 = Image.new("L", (10, 10), color=0)  # Black
        img1.save(images_dir / "test.png")
        results1 = generate_assets(width=10)
        content1 = (generated_dir / "test.txt").read_text()
        
        # Replace with different image
        img2 = Image.new("L", (10, 10), color=255)  # White
        img2.save(images_dir / "test.png")
        results2 = generate_assets(width=10)
        content2 = (generated_dir / "test.txt").read_text()
        
        assert content1 != content2

    def test_generate_assets_creates_cache_file(self, tmp_path, monkeypatch):
        """Test that cache file is created."""
        images_dir = tmp_path / "images"
        generated_dir = tmp_path / "generated"
        cache_file = generated_dir / ".cache.json"
        images_dir.mkdir()
        
        img = Image.new("L", (10, 10), color=128)
        img.save(images_dir / "test.png")
        
        monkeypatch.setattr(
            "cardio.assets.ascii_art_generator.IMAGES_DIR", images_dir
        )
        monkeypatch.setattr(
            "cardio.assets.ascii_art_generator.GENERATED_DIR", generated_dir
        )
        monkeypatch.setattr(
            "cardio.assets.ascii_art_generator.CACHE_FILE", cache_file
        )
        
        generate_assets(width=10)
        
        assert cache_file.exists()
        cache = json.loads(cache_file.read_text())
        assert "test.png" in cache
        assert "hash" in cache["test.png"]
        assert cache["test.png"]["width"] == 10


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


class TestModuleExports:
    """Test that all expected items are exported from the package."""

    def test_exports_from_package(self):
        """Test that key items are importable from cardio.assets."""
        from cardio.assets import (
            ASSETS_DIR,
            IMAGES_DIR,
            GENERATED_DIR,
            AsciiArtGenerator,
            AsciiArtGeneratorError,
            ImageNotFoundError,
            InvalidImageError,
            image_to_ascii_art,
            generate_assets,
        )
        
        assert ASSETS_DIR is not None
        assert IMAGES_DIR is not None
        assert GENERATED_DIR is not None
        assert AsciiArtGenerator is not None
        assert image_to_ascii_art is not None
        assert generate_assets is not None
