"""Tests for base watcher interface."""

import pytest
from sentinel.base import BaseWatcher
from sentinel.filesystem import FileSystemWatcher
from sentinel.config import WatcherConfig


def test_base_watcher_interface():
    """Test BaseWatcher defines required methods."""
    assert hasattr(BaseWatcher, "start")
    assert hasattr(BaseWatcher, "stop")
    assert hasattr(BaseWatcher, "on_new_item")


def test_filesystem_watcher_implements_base(mock_config):
    """Test FileSystemWatcher implements BaseWatcher."""
    watcher = FileSystemWatcher(mock_config)

    assert isinstance(watcher, BaseWatcher)
    assert callable(watcher.start)
    assert callable(watcher.stop)
    assert callable(watcher.on_new_item)


def test_watcher_name_property(mock_config):
    """Test watcher name property."""
    watcher = FileSystemWatcher(mock_config)

    assert watcher.name == "FileSystemWatcher"


def test_watcher_is_running_property(mock_config):
    """Test watcher is_running property."""
    watcher = FileSystemWatcher(mock_config)

    assert not watcher.is_running  # Initially false
