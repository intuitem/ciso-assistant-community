"""Tests for utility functions."""

import os
import tempfile
import pytest

from ..utils import (
    resolve_context_value,
    find_placeholders,
    sanitize_filename,
    generate_unique_media_name,
)


class TestResolveContextValue:
    """Test cases for resolve_context_value."""

    def test_simple_key(self):
        """Simple key lookup should work."""
        context = {"name": "John"}
        assert resolve_context_value(context, "name") == "John"

    def test_nested_key(self):
        """Nested key lookup via dot notation should work."""
        context = {"user": {"name": "John", "age": 30}}
        assert resolve_context_value(context, "user.name") == "John"
        assert resolve_context_value(context, "user.age") == 30

    def test_deeply_nested(self):
        """Deeply nested lookup should work."""
        context = {"a": {"b": {"c": {"d": "value"}}}}
        assert resolve_context_value(context, "a.b.c.d") == "value"

    def test_missing_key(self):
        """Missing key should return None."""
        context = {"name": "John"}
        assert resolve_context_value(context, "missing") is None

    def test_missing_nested_key(self):
        """Missing nested key should return None."""
        context = {"user": {"name": "John"}}
        assert resolve_context_value(context, "user.email") is None

    def test_object_attribute(self):
        """Should work with object attributes."""

        class User:
            def __init__(self):
                self.name = "John"

        context = {"user": User()}
        assert resolve_context_value(context, "user.name") == "John"


class TestFindPlaceholders:
    """Test cases for find_placeholders."""

    def test_no_placeholders(self):
        """Text without placeholders should return empty list."""
        assert find_placeholders("Hello World") == []

    def test_single_placeholder(self):
        """Single placeholder should be found."""
        result = find_placeholders("Hello {{name}}")
        assert len(result) == 1
        assert result[0][0] == "name"

    def test_multiple_placeholders(self):
        """Multiple placeholders should all be found."""
        result = find_placeholders("{{greeting}} {{name}}!")
        assert len(result) == 2
        assert result[0][0] == "greeting"
        assert result[1][0] == "name"

    def test_placeholder_positions(self):
        """Placeholder positions should be correct."""
        text = "Hello {{name}}!"
        result = find_placeholders(text)
        assert result[0][1] == 6  # Start position
        assert result[0][2] == 14  # End position

    def test_image_placeholder(self):
        """Image placeholders should be found."""
        result = find_placeholders("{{image:logo}}")
        assert len(result) == 1
        assert result[0][0] == "image:logo"

    def test_nested_placeholder(self):
        """Nested dot notation should be captured."""
        result = find_placeholders("{{user.name}}")
        assert result[0][0] == "user.name"


class TestSanitizeFilename:
    """Test cases for sanitize_filename."""

    def test_normal_filename(self):
        """Normal filename should pass through."""
        assert sanitize_filename("image.png") == "image.png"

    def test_path_traversal(self):
        """Path traversal attempts should be blocked."""
        assert sanitize_filename("../../../etc/passwd") == "passwd"
        assert sanitize_filename("/etc/passwd") == "passwd"

    def test_special_characters(self):
        """Special characters should be replaced."""
        result = sanitize_filename("file<>:name.png")
        assert "<" not in result
        assert ">" not in result
        assert ":" not in result

    def test_preserves_extension(self):
        """File extension should be preserved."""
        result = sanitize_filename("my file.png")
        assert result.endswith(".png")


class TestGenerateUniqueMediaName:
    """Test cases for generate_unique_media_name."""

    def test_first_file(self):
        """First file should be image1."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = generate_unique_media_name(tmpdir, ".png")
            assert result == "image1.png"

    def test_increments_counter(self):
        """Counter should increment for existing files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create existing file
            open(os.path.join(tmpdir, "image1.png"), "w").close()

            result = generate_unique_media_name(tmpdir, ".png")
            assert result == "image2.png"

    def test_finds_gap(self):
        """Should find first available number."""
        with tempfile.TemporaryDirectory() as tmpdir:
            open(os.path.join(tmpdir, "image1.png"), "w").close()
            open(os.path.join(tmpdir, "image2.png"), "w").close()
            # Gap at 3
            open(os.path.join(tmpdir, "image4.png"), "w").close()

            result = generate_unique_media_name(tmpdir, ".png")
            assert result == "image3.png"
