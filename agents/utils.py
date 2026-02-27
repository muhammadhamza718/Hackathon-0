"""Shared utility functions for AI Employee agents."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path


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
