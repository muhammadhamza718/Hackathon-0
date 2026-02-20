"""Tests for file system watcher."""

import pytest
import time
from pathlib import Path
from sentinel.filesystem import FileSystemWatcher, EventHandler
from sentinel.config import WatcherConfig


def test_event_handler_ignores_dot_files(mock_config):
    """Test EventHandler ignores dot-files."""
    handler = EventHandler(
        mock_config,
        __import__("queue").Queue(),
        set(),
    )

    source, _ = mock_config.watch_directory, mock_config.vault_inbox_path

    # Create dot-file
    dot_file = source / ".hidden"
    dot_file.touch()

    assert handler._is_ignored(dot_file)


def test_event_handler_ignores_tmp_files(mock_config):
    """Test EventHandler ignores .tmp files."""
    handler = EventHandler(
        mock_config,
        __import__("queue").Queue(),
        set(),
    )

    tmp_file = mock_config.watch_directory / "file.tmp"
    tmp_file.touch()

    assert handler._is_ignored(tmp_file)


def test_event_handler_allows_md(mock_config):
    """Test EventHandler allows .md files."""
    handler = EventHandler(
        mock_config,
        __import__("queue").Queue(),
        set(),
    )

    assert handler._is_allowed(Path("test.md"))


def test_event_handler_allows_pdf(mock_config):
    """Test EventHandler allows .pdf files."""
    handler = EventHandler(
        mock_config,
        __import__("queue").Queue(),
        set(),
    )

    assert handler._is_allowed(Path("test.pdf"))


def test_event_handler_rejects_exe(mock_config):
    """Test EventHandler rejects .exe files."""
    handler = EventHandler(
        mock_config,
        __import__("queue").Queue(),
        set(),
    )

    assert not handler._is_allowed(Path("test.exe"))


def test_file_move_success(mock_config):
    """Test successful file move."""
    watcher = FileSystemWatcher(mock_config)

    # Create source file
    source = mock_config.watch_directory / "test.md"
    source.write_text("# Test")

    # Move to inbox
    dest = watcher._move_to_inbox(source)

    assert dest.exists()
    assert dest.parent == mock_config.vault_inbox_path
    assert dest.name == "test.md"
    assert not source.exists()


def test_file_collision_resolution(mock_config):
    """Test filename collision resolution."""
    watcher = FileSystemWatcher(mock_config)

    # Create first file
    dest1 = mock_config.vault_inbox_path / "test.md"
    dest1.write_text("# First")

    # Create source file with same name
    source = mock_config.watch_directory / "test.md"
    source.write_text("# Second")

    # Move should create timestamped version
    dest2 = watcher._move_to_inbox(source)

    assert dest2.exists()
    assert dest1.exists()  # Original untouched
    assert dest2.name != "test.md"  # Different name
    assert dest2.stem.startswith("test_")  # Timestamp appended


def test_stability_check_immediate(mock_config):
    """Test stability check on static file."""
    watcher = FileSystemWatcher(mock_config)

    # Create static file
    source = mock_config.watch_directory / "test.md"
    source.write_text("# Test")

    # Stability check should pass immediately
    assert watcher._wait_for_stability(source, timeout=2.0)


def test_stability_check_timeout(mock_config):
    """Test stability check timeout on missing file."""
    watcher = FileSystemWatcher(mock_config)

    # Non-existent file
    source = mock_config.watch_directory / "missing.md"

    # Stability check should fail
    assert not watcher._wait_for_stability(source, timeout=0.5)


def test_directory_validation_creates_source(mock_config):
    """Test directory validation creates source if missing."""
    # Remove source directory
    mock_config.watch_directory.rmdir()
    assert not mock_config.watch_directory.exists()

    watcher = FileSystemWatcher(mock_config)
    watcher._validate_directories()

    # Source should be created
    assert mock_config.watch_directory.exists()


def test_directory_validation_fails_missing_inbox(mock_config):
    """Test directory validation fails if inbox missing."""
    # Remove inbox directory
    mock_config.vault_inbox_path.rmdir()
    assert not mock_config.vault_inbox_path.exists()

    watcher = FileSystemWatcher(mock_config)

    with pytest.raises(ValueError, match="Inbox"):
        watcher._validate_directories()
