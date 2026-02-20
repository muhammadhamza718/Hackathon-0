"""Mock watcher for testing extensibility."""

from pathlib import Path
from sentinel.base import BaseWatcher


class MockWatcher(BaseWatcher):
    """Mock watcher for testing BaseWatcher interface."""

    def __init__(self):
        """Initialize mock watcher."""
        self._running = False

    def start(self) -> None:
        """Start (no-op for mock)."""
        self._running = True

    def stop(self) -> None:
        """Stop (no-op for mock)."""
        self._running = False

    def on_new_item(self, path: Path) -> None:
        """Handle new item (no-op for mock)."""
        pass

    @property
    def is_running(self) -> bool:
        """Check if running."""
        return self._running
