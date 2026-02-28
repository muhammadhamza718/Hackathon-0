"""Event types for sentinel file system monitoring."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path


class EventType(Enum):
    """Types of file system events."""
    CREATED = "created"
    MODIFIED = "modified"
    DELETED = "deleted"
    MOVED = "moved"


@dataclass(frozen=True)
class FileEvent:
    """Represents a file system event detected by the watcher.

    Attributes:
        event_type: The type of event (created, modified, deleted, moved).
        path: Path to the affected file.
        timestamp: UTC timestamp when the event was detected.
        dest_path: Destination path (only for MOVED events).
    """
    event_type: EventType
    path: Path
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    dest_path: Path | None = None

    @property
    def filename(self) -> str:
        """Return just the filename."""
        return self.path.name

    @property
    def extension(self) -> str:
        """Return the file extension (lowercase)."""
        return self.path.suffix.lower()

    @property
    def is_markdown(self) -> bool:
        """Check if the file is a markdown file."""
        return self.extension == ".md"

    def __str__(self) -> str:
        ts = self.timestamp.strftime("%H:%M:%S")
        return f"[{ts}] {self.event_type.value}: {self.filename}"
