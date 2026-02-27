"""Unit tests for sentinel WatcherConfig."""

from __future__ import annotations

from pathlib import Path

import pytest

from sentinel.config import WatcherConfig


@pytest.fixture
def valid_config(tmp_path: Path) -> WatcherConfig:
    watch_dir = tmp_path / "watch"
    inbox = tmp_path / "vault" / "Inbox"
    watch_dir.mkdir()
    inbox.mkdir(parents=True)
    return WatcherConfig(
        watch_directory=watch_dir,
        vault_inbox_path=inbox,
    )


def test_valid_config_created(valid_config: WatcherConfig):
    assert valid_config.watch_directory.exists()
    assert valid_config.vault_inbox_path.exists()


def test_default_stability_seconds(valid_config: WatcherConfig):
    assert valid_config.stability_seconds == 2.0


def test_default_log_level(valid_config: WatcherConfig):
    assert valid_config.log_level == "INFO"


def test_default_extensions(valid_config: WatcherConfig):
    assert ".md" in valid_config.allowed_extensions


def test_string_paths_converted(tmp_path: Path):
    watch_dir = tmp_path / "w"
    inbox = tmp_path / "i"
    watch_dir.mkdir()
    inbox.mkdir()
    cfg = WatcherConfig(
        watch_directory=str(watch_dir),
        vault_inbox_path=str(inbox),
    )
    assert isinstance(cfg.watch_directory, Path)
    assert isinstance(cfg.vault_inbox_path, Path)


def test_empty_watch_directory_raises():
    with pytest.raises(ValueError, match="WATCH_DIRECTORY"):
        WatcherConfig(watch_directory="", vault_inbox_path=Path("/tmp"))
