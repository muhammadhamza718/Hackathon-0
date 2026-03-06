"""Sentinel: File system watcher for Obsidian Vault ingestion (Bronze Tier)."""

from sentinel.base import BaseWatcher
from sentinel.config import WatcherConfig
from sentinel.events import EventType, FileEvent
from sentinel.filesystem import FileSystemWatcher
from sentinel.health import HealthChecker, HealthState, HealthStatus

__version__ = "0.3.0"
__all__ = [
    "BaseWatcher",
    "WatcherConfig",
    "EventType",
    "FileEvent",
    "FileSystemWatcher",
    "HealthChecker",
    "HealthState",
    "HealthStatus",
    "__version__",
]
