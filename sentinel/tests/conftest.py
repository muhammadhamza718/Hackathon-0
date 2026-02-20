"""Pytest configuration and fixtures."""

import pytest
from pathlib import Path
from sentinel.config import WatcherConfig


@pytest.fixture
def temp_source_inbox(tmp_path):
    """Create temporary source and inbox directories.

    Returns:
        Tuple of (source_dir, inbox_dir).
    """
    source = tmp_path / "source"
    inbox = tmp_path / "inbox"
    source.mkdir()
    inbox.mkdir()
    return source, inbox


@pytest.fixture
def mock_config(temp_source_inbox):
    """Create a mock WatcherConfig for testing.

    Returns:
        WatcherConfig instance.
    """
    source, inbox = temp_source_inbox
    return WatcherConfig(
        watch_directory=source,
        vault_inbox_path=inbox,
        stability_seconds=0.5,
        allowed_extensions=".md,.txt,.pdf,.jpg,.jpeg,.png",
        log_level="DEBUG",
    )
