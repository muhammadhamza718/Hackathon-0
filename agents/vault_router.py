"""Vault file routing logic for the Bronze Tier agent."""

from __future__ import annotations

import re
import shutil
from pathlib import Path

from agents.constants import (
    DONE_DIR,
    INBOX_DIR,
    NEEDS_ACTION_DIR,
    PENDING_APPROVAL_DIR,
)


def classify_task(content: str) -> str:
    """Classify a task file as simple or complex.

    A task is complex if it mentions external actions, multi-step work,
    or contains HITL markers.

    Args:
        content: Markdown content of the task file.

    Returns:
        "complex" or "simple"
    """
    complex_signals = [
        r"(?i)\bexternal\b",
        r"(?i)\bapi\b",
        r"(?i)\bemail\b",
        r"(?i)\bpayment\b",
        r"(?i)\bmulti[- ]?step\b",
        r"✋",
    ]
    for pattern in complex_signals:
        if re.search(pattern, content):
            return "complex"
    return "simple"


def route_file(file_path: Path, vault_root: Path) -> Path:
    """Route an Inbox file to the appropriate vault folder.

    Args:
        file_path: Path to the file in Inbox.
        vault_root: Root directory of the vault.

    Returns:
        Destination path after routing.

    Raises:
        FileNotFoundError: If source file does not exist.
    """
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    content = file_path.read_text(encoding="utf-8")
    classification = classify_task(content)

    if classification == "complex":
        dest_dir = vault_root / PENDING_APPROVAL_DIR
    else:
        dest_dir = vault_root / NEEDS_ACTION_DIR

    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / file_path.name

    shutil.move(str(file_path), str(dest))
    return dest


def mark_done(file_path: Path, vault_root: Path) -> Path:
    """Move a completed task file to Done.

    Args:
        file_path: Path to the completed task file.
        vault_root: Root directory of the vault.

    Returns:
        Destination path in Done folder.
    """
    done_dir = vault_root / DONE_DIR
    done_dir.mkdir(parents=True, exist_ok=True)
    dest = done_dir / file_path.name
    shutil.move(str(file_path), str(dest))
    return dest
