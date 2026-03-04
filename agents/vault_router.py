"""Vault file routing logic for the Bronze Tier agent."""

from __future__ import annotations

import re
import shutil
from dataclasses import dataclass
from enum import Enum, unique
from pathlib import Path

from agents.constants import (
    DONE_DIR,
    INBOX_DIR,
    NEEDS_ACTION_DIR,
    PENDING_APPROVAL_DIR,
)


@unique
class TaskClassification(Enum):
    """Classification result for an inbox task."""

    SIMPLE = "simple"
    COMPLEX = "complex"


_COMPLEX_SIGNALS: list[tuple[str, str]] = [
    (r"(?i)\bexternal\b", "references external system"),
    (r"(?i)\bapi\b", "involves API interaction"),
    (r"(?i)\bemail\b", "requires sending email"),
    (r"(?i)\bpayment\b", "involves payment processing"),
    (r"(?i)\bmulti[- ]?step\b", "multi-step workflow"),
    (r"✋", "HITL marker present"),
]


@dataclass(frozen=True)
class ClassificationResult:
    """Result of task classification with reasoning trail."""

    classification: TaskClassification
    matched_signals: tuple[str, ...]

    @property
    def is_complex(self) -> bool:
        return self.classification is TaskClassification.COMPLEX


def classify_task(content: str) -> TaskClassification:
    """Classify a task file as simple or complex.

    Args:
        content: Markdown content of the task file.

    Returns:
        ``TaskClassification.COMPLEX`` or ``TaskClassification.SIMPLE``.
    """
    return classify_task_detailed(content).classification


def classify_task_detailed(content: str) -> ClassificationResult:
    """Classify with full reasoning trail.

    Args:
        content: Markdown content of the task file.

    Returns:
        A ``ClassificationResult`` with matched signal descriptions.
    """
    matched: list[str] = []
    for pattern, reason in _COMPLEX_SIGNALS:
        if re.search(pattern, content):
            matched.append(reason)

    if matched:
        return ClassificationResult(
            classification=TaskClassification.COMPLEX,
            matched_signals=tuple(matched),
        )
    return ClassificationResult(
        classification=TaskClassification.SIMPLE,
        matched_signals=(),
    )


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
    result = classify_task_detailed(content)

    if result.is_complex:
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
