"""Sentinel: File system watcher for Obsidian Vault ingestion (Bronze Tier)."""

from sentinel.base import BaseWatcher
from sentinel.config import WatcherConfig
from sentinel.filesystem import FileSystemWatcher

__version__ = "0.1.0"
__all__ = [
    "BaseWatcher",
    "WatcherConfig",
    "FileSystemWatcher",
    "__version__",
]
