"""HITL (Human-In-The-Loop) approval gate for Silver Tier."""

from __future__ import annotations

import shutil
from enum import Enum, unique
from pathlib import Path

from agents.constants import APPROVED_DIR, PENDING_APPROVAL_DIR, REJECTED_DIR
from agents.utils import ensure_dir


@unique
class Decision(Enum):
    """Outcome of a human review decision."""

    APPROVED = "approved"
    REJECTED = "rejected"
    PENDING = "pending"

    @property
    def is_final(self) -> bool:
        """True when the decision is terminal (not pending)."""
        return self is not Decision.PENDING


class HITLGate:
    """Gate that blocks external actions until human approval."""

    def __init__(self, vault_root: Path) -> None:
        self.vault_root = vault_root
        self.pending_dir = ensure_dir(vault_root / PENDING_APPROVAL_DIR)
        self.approved_dir = ensure_dir(vault_root / APPROVED_DIR)
        self.rejected_dir = ensure_dir(vault_root / REJECTED_DIR)

    def submit_for_approval(self, file_path: Path) -> Path:
        """Move a file to Pending_Approval for human review.

        Args:
            file_path: Path to the file requiring approval.

        Returns:
            Path in the Pending_Approval directory.

        Raises:
            FileNotFoundError: If source file doesn't exist.
        """
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        dest = self.pending_dir / file_path.name
        shutil.move(str(file_path), str(dest))
        return dest

    def get_pending(self) -> list[Path]:
        """List all files awaiting approval.

        Returns:
            List of file paths in Pending_Approval.
        """
        return sorted(self.pending_dir.glob("*.md"))

    def is_approved(self, filename: str) -> bool:
        """Check if a file has been approved.

        Args:
            filename: Name of the file to check.

        Returns:
            True if the file exists in Approved directory.
        """
        return (self.approved_dir / filename).exists()

    def is_rejected(self, filename: str) -> bool:
        """Check if a file has been rejected.

        Args:
            filename: Name of the file to check.

        Returns:
            True if the file exists in Rejected directory.
        """
        return (self.rejected_dir / filename).exists()

    def check_decision(self, filename: str) -> Decision:
        """Check the human decision for a pending item.

        Args:
            filename: Name of the file.

        Returns:
            ``Decision`` enum value.
        """
        if self.is_approved(filename):
            return Decision.APPROVED
        if self.is_rejected(filename):
            return Decision.REJECTED
        return Decision.PENDING

    @property
    def pending_count(self) -> int:
        """Return number of items awaiting approval."""
        return len(self.get_pending())
