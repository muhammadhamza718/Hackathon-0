"""Inbox scanner — discovers and prioritizes files in /Inbox/."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import IntEnum, unique
from pathlib import Path

from agents.constants import INBOX_DIR, MAX_INBOX_SCAN_FILES


@unique
class Priority(IntEnum):
    """Task priority levels ordered by urgency (lower value = higher urgency)."""

    CRITICAL = 0
    HIGH = 1
    MEDIUM = 2
    LOW = 3

    @classmethod
    def from_string(cls, value: str) -> Priority:
        """Parse a priority string, defaulting to MEDIUM for unknowns."""
        try:
            return cls[value.upper()]
        except KeyError:
            return cls.MEDIUM


@dataclass(frozen=True)
class ScanResult:
    """A scanned inbox file with its extracted priority."""

    path: Path
    priority: Priority

    @property
    def is_urgent(self) -> bool:
        """True when priority is CRITICAL or HIGH."""
        return self.priority <= Priority.HIGH


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
    files = list(inbox.glob("*.md"))[:MAX_INBOX_SCAN_FILES]
    return sorted(files, key=lambda f: f.stat().st_mtime, reverse=True)


def extract_priority(content: str) -> Priority:
    """Extract priority from task file content.

    Looks for a line like ``Priority: high`` (case-insensitive).

    Args:
        content: File content.

    Returns:
        Parsed ``Priority`` enum value, defaulting to ``Priority.MEDIUM``.
    """
    match = re.search(r"(?i)priority:\s*(critical|high|medium|low)", content)
    if match:
        return Priority.from_string(match.group(1))
    return Priority.MEDIUM


def prioritize_inbox(vault_root: Path) -> list[ScanResult]:
    """Scan inbox and return files with their priorities.

    Args:
        vault_root: Root directory of the vault.

    Returns:
        List of ``ScanResult`` sorted by priority (most urgent first).
    """
    files = scan_inbox(vault_root)
    results: list[ScanResult] = []
    for f in files:
        content = f.read_text(encoding="utf-8")
        pri = extract_priority(content)
        results.append(ScanResult(path=f, priority=pri))
    return sorted(results, key=lambda r: r.priority)
