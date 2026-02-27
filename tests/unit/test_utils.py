"""Unit tests for agents.utils module."""

from __future__ import annotations

from pathlib import Path

import pytest

from agents.utils import ensure_dir, safe_read, slugify, utcnow_iso


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
