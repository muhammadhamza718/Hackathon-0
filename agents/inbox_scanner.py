"""Inbox scanner — discovers and prioritizes files in /Inbox/."""

from __future__ import annotations

import re
from pathlib import Path

from agents.constants import INBOX_DIR


def scan_inbox(vault_root: Path) -> list[Path]:
    """List all markdown files in Inbox, sorted newest first.

    Args:
        vault_root: Root directory of the vault.

    Returns:
        List of file paths sorted by modification time (newest first).
    """
    inbox = vault_root / INBOX_DIR
    if not inbox.exists():
        return []
    files = list(inbox.glob("*.md"))
    return sorted(files, key=lambda f: f.stat().st_mtime, reverse=True)


def extract_priority(content: str) -> str:
    """Extract priority from task file content.

    Looks for a line like "Priority: high" (case-insensitive).

    Args:
        content: File content.

    Returns:
        Priority string ("high", "medium", "low") or "medium" as default.
    """
    match = re.search(r"(?i)priority:\s*(high|medium|low)", content)
    if match:
        return match.group(1).lower()
    return "medium"


def prioritize_inbox(vault_root: Path) -> list[tuple[Path, str]]:
    """Scan inbox and return files with their priorities.

    Args:
        vault_root: Root directory of the vault.

    Returns:
        List of (path, priority) tuples sorted: high > medium > low.
    """
    order = {"high": 0, "medium": 1, "low": 2}
    files = scan_inbox(vault_root)
    items = []
    for f in files:
        content = f.read_text(encoding="utf-8")
        pri = extract_priority(content)
        items.append((f, pri))
    return sorted(items, key=lambda x: order.get(x[1], 1))
