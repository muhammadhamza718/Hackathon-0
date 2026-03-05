"""Vault initialization — creates required directory structure."""

from __future__ import annotations

from dataclasses import dataclass
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


@dataclass(frozen=True)
class InitResult:
    """Immutable result of vault initialization."""

    created_dirs: tuple[Path, ...]
    created_files: tuple[Path, ...]
    vault_root: Path

    @property
    def total_created(self) -> int:
        """Total number of new directories and files created."""
        return len(self.created_dirs) + len(self.created_files)

    @property
    def was_fresh(self) -> bool:
        """True when something was actually created (not pre-existing)."""
        return self.total_created > 0


def init_vault(vault_root: Path) -> InitResult:
    """Initialize vault directory structure.

    Creates all required directories if they don't exist.

    Args:
        vault_root: Root directory for the vault.

    Returns:
        ``InitResult`` with created directories and files.
    """
    created_dirs: list[Path] = []
    created_files: list[Path] = []
    for dirname in REQUIRED_DIRS:
        dirpath = vault_root / dirname
        if not dirpath.exists():
            dirpath.mkdir(parents=True)
            created_dirs.append(dirpath)

    # Create empty Dashboard.md if not present
    dashboard = vault_root / DASHBOARD_FILE
    if not dashboard.exists():
        dashboard.write_text(
            "# Dashboard\n\n*Run the agent to populate this file.*\n",
            encoding="utf-8",
        )
        created_files.append(dashboard)

    return InitResult(
        created_dirs=tuple(created_dirs),
        created_files=tuple(created_files),
        vault_root=vault_root,
    )


def is_vault_initialized(vault_root: Path) -> bool:
    """Check if a vault has all required directories.

    Args:
        vault_root: Root directory to check.

    Returns:
        True if all required directories exist.
    """
    return all((vault_root / d).is_dir() for d in REQUIRED_DIRS)
