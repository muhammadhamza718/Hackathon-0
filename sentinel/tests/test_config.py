"""Tests for configuration management."""

import os
import pytest
from pathlib import Path
from sentinel.config import WatcherConfig, load_from_env


def test_watcher_config_valid(tmp_path):
    """Test WatcherConfig with valid paths."""
    source = tmp_path / "source"
    inbox = tmp_path / "inbox"
    source.mkdir()
    inbox.mkdir()

    config = WatcherConfig(
        watch_directory=source,
        vault_inbox_path=inbox,
    )

    assert config.watch_directory == source
    assert config.vault_inbox_path == inbox
    assert config.stability_seconds == 2.0
    assert config.log_level == "INFO"


def test_watcher_config_string_paths(tmp_path):
    """Test WatcherConfig converts string paths to Path."""
    source = tmp_path / "source"
    inbox = tmp_path / "inbox"
    source.mkdir()
    inbox.mkdir()

    config = WatcherConfig(
        watch_directory=str(source),
        vault_inbox_path=str(inbox),
    )

    assert isinstance(config.watch_directory, Path)
    assert isinstance(config.vault_inbox_path, Path)


def test_watcher_config_missing_watch_dir():
    """Test WatcherConfig fails without watch directory."""
    with pytest.raises(ValueError, match="WATCH_DIRECTORY"):
        WatcherConfig(
            watch_directory="",
            vault_inbox_path="/tmp/inbox",
        )


def test_watcher_config_missing_inbox_path():
    """Test WatcherConfig fails without inbox path."""
    with pytest.raises(ValueError, match="VAULT_INBOX_PATH"):
        WatcherConfig(
            watch_directory="/tmp/source",
            vault_inbox_path="",
        )


def test_watcher_config_invalid_stability():
    """Test WatcherConfig fails with invalid stability seconds."""
    with pytest.raises(ValueError, match="STABILITY_SECONDS"):
        WatcherConfig(
            watch_directory="/tmp/source",
            vault_inbox_path="/tmp/inbox",
            stability_seconds=0.1,
        )


def test_watcher_config_invalid_log_level(tmp_path):
    """Test WatcherConfig fails with invalid log level."""
    source = tmp_path / "source"
    inbox = tmp_path / "inbox"
    source.mkdir()
    inbox.mkdir()

    with pytest.raises(ValueError, match="LOG_LEVEL"):
        WatcherConfig(
            watch_directory=source,
            vault_inbox_path=inbox,
            log_level="INVALID",
        )


def test_load_from_env_missing_required(monkeypatch):
    """Test load_from_env fails when required vars missing."""
    monkeypatch.delenv("WATCH_DIRECTORY", raising=False)
    monkeypatch.delenv("VAULT_INBOX_PATH", raising=False)

    with pytest.raises(ValueError, match="required"):
        load_from_env()
