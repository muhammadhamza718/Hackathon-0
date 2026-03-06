"""Shared utility functions for AI Employee agents."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

__all__ = [
    "utcnow_iso",
    "slugify",
    "ensure_dir",
    "safe_read",
    "safe_write",
    "file_exists",
    "is_markdown",
    "truncate",
    "clamp",
]


def utcnow_iso() -> str:
    """Return current UTC time as ISO-8601 string."""
    return datetime.now(timezone.utc).isoformat()


def slugify(text: str) -> str:
    """Convert text to a URL-safe slug.

    Args:
        text: Input string to slugify.

    Returns:
        Lowercase hyphen-separated slug.
    """
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text


def ensure_dir(path: Path) -> Path:
    """Create directory and parents if they don't exist.

    Args:
        path: Directory path to create.

    Returns:
        The path after creation.
    """
    path.mkdir(parents=True, exist_ok=True)
    return path


def safe_read(path: Path) -> str | None:
    """Read file contents safely, returning None on error.

    Args:
        path: File path to read.

    Returns:
        File contents as string, or None if unreadable.
    """
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def file_exists(path: Path) -> bool:
    """Check if a path exists and is a file (not a directory)."""
    return path.exists() and path.is_file()


def is_markdown(path: Path) -> bool:
    """Check if a file path has a .md extension."""
    return path.suffix.lower() == ".md"


def truncate(text: str, max_len: int = 80) -> str:
    """Truncate text to max length with ellipsis."""
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."


def clamp(value: int, low: int, high: int) -> int:
    """Clamp an integer to [low, high] range inclusive.

    Args:
        value: The value to clamp.
        low: Minimum allowed value.
        high: Maximum allowed value.

    Returns:
        The clamped value.
    """
    return max(low, min(value, high))


def safe_write(path: Path, content: str) -> bool:
    """Write content to a file, returning success status.

    Args:
        path: File path to write.
        content: String content to write.

    Returns:
        True if written successfully, False on error.
    """
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return True
    except OSError:
        return False
