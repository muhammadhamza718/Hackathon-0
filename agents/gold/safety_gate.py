"""Gold-tier safety gate — extends Silver HITL with $100 threshold and social gating.

Per Constitution XV every payment > $100, every public social post, and
every Odoo write operation MUST be routed to ``/Pending_Approval/``.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

from agents.constants import PAYMENT_APPROVAL_THRESHOLD, PENDING_APPROVAL_DIR
from agents.hitl_gate import Decision, HITLGate
from agents.utils import ensure_dir, slugify


class GoldSafetyGate:
    """Gold-tier HITL gate wrapping the Silver ``HITLGate``."""

    def __init__(
        self,
        vault_root: Path,
        payment_threshold: float = PAYMENT_APPROVAL_THRESHOLD,
    ) -> None:
        self.vault_root = vault_root
        self.payment_threshold = payment_threshold
        self._gate = HITLGate(vault_root)

    # ------------------------------------------------------------------
    # Detection helpers
    # ------------------------------------------------------------------

    @staticmethod
    def is_social_post(action_type: str) -> bool:
        """Return True if the action is a public social media post."""
        return action_type in {"social_draft", "social_post"}

    def exceeds_payment_threshold(self, amount: float) -> bool:
        """Return True if *amount* exceeds the configured threshold."""
        return amount > self.payment_threshold

    @staticmethod
    def is_odoo_write(action_type: str) -> bool:
        """Return True if the action is an Odoo write operation."""
        return action_type in {"odoo_write_draft"}

    def requires_approval(
        self,
        action_type: str,
        amount: float = 0.0,
    ) -> bool:
        """Check whether the given action requires HITL approval.

        Args:
            action_type: The Gold action string.
            amount: Monetary amount (used for payment threshold check).

        Returns:
            True if the action must go through ``/Pending_Approval/``.
        """
        if self.is_social_post(action_type):
            return True
        if self.is_odoo_write(action_type):
            return True
        if self.exceeds_payment_threshold(amount):
            return True
        return False

    # ------------------------------------------------------------------
    # Approval workflow
    # ------------------------------------------------------------------

    def submit_for_approval(
        self,
        file_path: Path,
    ) -> Path:
        """Delegate to the underlying Silver HITL gate."""
        return self._gate.submit_for_approval(file_path)

    def create_approval_file(
        self,
        *,
        action_type: str,
        content: str,
        rationale: str,
        amount: float | None = None,
        platform: str | None = None,
        risk_level: str = "Medium",
    ) -> Path:
        """Write an approval request to ``/Pending_Approval/``.

        Returns:
            Path to the created approval file.
        """
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        slug = slugify(action_type)
        filename = f"{ts.replace(':', '-')}_{slug}.md"

        # Build YAML frontmatter
        lines = [
            "---",
            f"type: {action_type}",
        ]
        if platform:
            lines.append(f"platform: {platform}")
        if amount is not None:
            lines.append(f"amount: {amount:.2f}")
        lines += [
            f"rationale: {rationale}",
            f"risk_level: {risk_level}",
            f"created: {ts}",
            "---",
            "",
            f"# Approval Request — {action_type}",
            "",
            content,
        ]

        pending_dir = ensure_dir(self.vault_root / PENDING_APPROVAL_DIR)
        dest = pending_dir / filename
        dest.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return dest

    def check_decision(self, filename: str) -> Decision:
        """Check the human decision for a pending item."""
        return self._gate.check_decision(filename)

    def is_approved(self, filename: str) -> bool:
        """Check if a file has been approved."""
        return self._gate.is_approved(filename)

    @property
    def pending_count(self) -> int:
        """Number of items awaiting approval."""
        return self._gate.pending_count
