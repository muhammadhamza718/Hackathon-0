"""Unit tests for agents.utils module."""

from __future__ import annotations

from pathlib import Path

import pytest

from agents.utils import clamp, ensure_dir, file_exists, is_markdown, safe_read, safe_write, slugify, truncate, utcnow_iso


class TestSlugify:
    def test_basic(self):
        assert slugify("Hello World") == "hello-world"

    def test_special_chars(self):
        assert slugify("Fix Bug #42!") == "fix-bug-42"

    def test_multiple_spaces(self):
        assert slugify("a  b   c") == "a-b-c"

    def test_already_slug(self):
        assert slugify("my-slug") == "my-slug"

    def test_uppercase(self):
        assert slugify("UPPER CASE") == "upper-case"


class TestUtcnowIso:
    def test_returns_string(self):
        result = utcnow_iso()
        assert isinstance(result, str)

    def test_contains_utc_marker(self):
        result = utcnow_iso()
        assert "+" in result or "Z" in result or "UTC" in result


class TestEnsureDir:
    def test_creates_directory(self, tmp_path: Path):
        target = tmp_path / "new" / "nested" / "dir"
        result = ensure_dir(target)
        assert result.exists()
        assert result.is_dir()

    def test_returns_path(self, tmp_path: Path):
        target = tmp_path / "mydir"
        result = ensure_dir(target)
        assert result == target

    def test_idempotent(self, tmp_path: Path):
        target = tmp_path / "existing"
        ensure_dir(target)
        ensure_dir(target)  # Should not raise
        assert target.exists()


class TestSafeRead:
    def test_reads_existing_file(self, tmp_path: Path):
        f = tmp_path / "test.txt"
        f.write_text("hello")
        assert safe_read(f) == "hello"

    def test_returns_none_for_missing(self, tmp_path: Path):
        assert safe_read(tmp_path / "missing.txt") is None


class TestFileExists:
    def test_existing_file(self, tmp_path: Path):
        f = tmp_path / "file.txt"
        f.write_text("x")
        assert file_exists(f) is True

    def test_missing_file(self, tmp_path: Path):
        assert file_exists(tmp_path / "nope.txt") is False

    def test_directory_returns_false(self, tmp_path: Path):
        assert file_exists(tmp_path) is False


class TestIsMarkdown:
    @pytest.mark.parametrize(
        "name,expected",
        [
            ("task.md", True),
            ("README.MD", True),
            ("image.png", False),
            ("data.json", False),
        ],
    )
    def test_extension_check(self, name: str, expected: bool):
        assert is_markdown(Path(name)) is expected


class TestTruncate:
    def test_short_text_unchanged(self):
        assert truncate("hello", 10) == "hello"

    def test_exact_length_unchanged(self):
        assert truncate("12345", 5) == "12345"

    def test_long_text_truncated(self):
        result = truncate("a" * 100, 10)
        assert len(result) == 10
        assert result.endswith("...")


class TestSafeWrite:
    def test_writes_content(self, tmp_path: Path):
        f = tmp_path / "test.txt"
        assert safe_write(f, "hello") is True
        assert f.read_text() == "hello"

    def test_creates_parent_dirs(self, tmp_path: Path):
        f = tmp_path / "nested" / "deep" / "file.txt"
        assert safe_write(f, "content") is True
        assert f.exists()

    def test_roundtrip_with_safe_read(self, tmp_path: Path):
        f = tmp_path / "roundtrip.md"
        safe_write(f, "# Title\n\nBody text.")
        assert safe_read(f) == "# Title\n\nBody text."


class TestClamp:
    @pytest.mark.parametrize(
        "value,low,high,expected",
        [
            (5, 0, 10, 5),
            (-1, 0, 10, 0),
            (15, 0, 10, 10),
            (0, 0, 0, 0),
            (5, 5, 5, 5),
        ],
    )
    def test_clamp_values(self, value: int, low: int, high: int, expected: int):
        assert clamp(value, low, high) == expected
