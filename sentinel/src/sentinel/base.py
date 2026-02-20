"""Abstract base class for file system watchers."""

from abc import ABC, abstractmethod
from pathlib import Path


class BaseWatcher(ABC):
    """Abstract base class for file system watchers.

    All concrete watcher implementations (FileSystem, Gmail, WhatsApp) must
    inherit from this class and implement the abstract methods.
    """

    @abstractmethod
    def start(self) -> None:
        """Start monitoring the input source.

        Blocks until stop() is called or interrupted.
        """
        pass

    @abstractmethod
    def stop(self) -> None:
        """Stop monitoring the input source.

        Gracefully completes any in-flight operations before returning.
        """
        pass

    @abstractmethod
    def on_new_item(self, path: Path) -> None:
        """Handle detection of a new item.

        Args:
            path: Path to the new file or item.
        """
        pass

    @property
    def name(self) -> str:
        """Human-readable name of the watcher.

        Returns:
            Watcher name (e.g., "FileSystemWatcher").
        """
        return self.__class__.__name__

    @property
    def is_running(self) -> bool:
        """Check if watcher is currently active.

        Returns:
            True if watcher is running, False otherwise.
        """
        return False  # Override in subclass
