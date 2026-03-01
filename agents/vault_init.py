"""Vault initialization — creates required directory structure."""

from __future__ import annotations

from pathlib import Path

from agents.constants import (
    APPROVED_DIR,
    DASHBOARD_FILE,
    DONE_DIR,
    INBOX_DIR,
    LOGS_DIR,
    NEEDS_ACTION_DIR,
    PENDING_APPROVAL_DIR,
    PLANS_DIR,
    REJECTED_DIR,
)

REQUIRED_DIRS = [
    INBOX_DIR,
    NEEDS_ACTION_DIR,
    DONE_DIR,
    PENDING_APPROVAL_DIR,
    APPROVED_DIR,
    REJECTED_DIR,
    PLANS_DIR,
    LOGS_DIR,
]


def init_vault(vault_root: Path) -> list[Path]:
    """Initialize vault directory structure.

    Creates all required directories if they don't exist.

    Args:
        vault_root: Root directory for the vault.

    Returns:
        List of directories that were created (already existing dirs excluded).
    """
    created: list[Path] = []
    for dirname in REQUIRED_DIRS:
        dirpath = vault_root / dirname
        if not dirpath.exists():
            dirpath.mkdir(parents=True)
            created.append(dirpath)

    # Create empty Dashboard.md if not present
    dashboard = vault_root / DASHBOARD_FILE
    if not dashboard.exists():
        dashboard.write_text(
            "# Dashboard\n\n*Run the agent to populate this file.*\n",
            encoding="utf-8",
        )
        created.append(dashboard)

    return created


def is_vault_initialized(vault_root: Path) -> bool:
    """Check if a vault has all required directories.

    Args:
        vault_root: Root directory to check.

    Returns:
        True if all required directories exist.
    """
    return all((vault_root / d).is_dir() for d in REQUIRED_DIRS)
