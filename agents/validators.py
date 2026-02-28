"""Input validation helpers for vault files and task content."""

from __future__ import annotations

import re
from pathlib import Path


def is_valid_plan_id(plan_id: str) -> bool:
    """Check if a plan ID matches the expected format.

    Expected format: PLAN-YYYY-NNN (e.g. PLAN-2026-001)

    Args:
        plan_id: The plan ID string to validate.

    Returns:
        True if valid, False otherwise.
    """
    return bool(re.match(r"^PLAN-\d{4}-\d{3}$", plan_id))


def is_valid_priority(priority: str) -> bool:
    """Check if a priority value is valid.

    Args:
        priority: Priority string to validate.

    Returns:
        True if valid (high, medium, low).
    """
    return priority in ("high", "medium", "low")


def is_valid_status(status: str) -> bool:
    """Check if a plan status value is valid.

    Args:
        status: Status string to validate.

    Returns:
        True if valid.
    """
    return status in ("draft", "active", "blocked", "complete", "approved", "rejected")


def has_frontmatter(content: str) -> bool:
    """Check if content has YAML frontmatter delimiters.

    Args:
        content: File content string.

    Returns:
        True if content starts with --- and has a closing ---.
    """
    return content.startswith("---") and "\n---" in content[3:]


def is_safe_filename(name: str) -> bool:
    """Check if a filename is safe (no path traversal, valid chars).

    Args:
        name: Filename to check.

    Returns:
        True if safe.
    """
    if not name:
        return False
    if ".." in name or "/" in name or "\\" in name:
        return False
    if name.startswith("."):
        return False
    return bool(re.match(r"^[\w\-. ]+$", name))


def validate_vault_structure(vault_root: Path) -> list[str]:
    """Validate that a vault has the required directory structure.

    Args:
        vault_root: Root path of the vault.

    Returns:
        List of error messages. Empty list means valid.
    """
    required = [
        "Inbox",
        "Needs_Action",
        "Done",
        "Pending_Approval",
        "Approved",
        "Rejected",
    ]
    errors = []
    for d in required:
        if not (vault_root / d).is_dir():
            errors.append(f"Missing required directory: {d}")
    return errors
