"""Tests for ignore pattern handling."""

import pytest
from sentinel.filesystem import EventHandler
from sentinel.config import WatcherConfig


def test_ignore_dot_lock(mock_config):
    """Test ignore .~lock files."""
    handler = EventHandler(
        mock_config,
        __import__("queue").Queue(),
        set(),
    )

    assert handler._is_ignored(mock_config.watch_directory / ".~lock.pdf")


def test_ignore_crdownload(mock_config):
    """Test ignore .crdownload files."""
    handler = EventHandler(
        mock_config,
        __import__("queue").Queue(),
        set(),
    )

    assert handler._is_ignored(
        mock_config.watch_directory / "file.pdf.crdownload"
    )


def test_ignore_dot_part(mock_config):
    """Test ignore .part files."""
    handler = EventHandler(
        mock_config,
        __import__("queue").Queue(),
        set(),
    )

    assert handler._is_ignored(mock_config.watch_directory / "file.part")


def test_ignore_tilde_prefix(mock_config):
    """Test ignore tilde-prefixed files."""
    handler = EventHandler(
        mock_config,
        __import__("queue").Queue(),
        set(),
    )

    assert handler._is_ignored(mock_config.watch_directory / "~file.md")


def test_allow_normal_files(mock_config):
    """Test normal files are not ignored."""
    handler = EventHandler(
        mock_config,
        __import__("queue").Queue(),
        set(),
    )

    assert not handler._is_ignored(mock_config.watch_directory / "note.md")
    assert not handler._is_ignored(mock_config.watch_directory / "doc.pdf")
    assert not handler._is_ignored(mock_config.watch_directory / "image.jpg")
