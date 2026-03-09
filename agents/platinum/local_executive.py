"""Local-only execution router for Platinum."""

from __future__ import annotations

import logging
from pathlib import Path

from agents.audit_logger import append_log
from agents.constants import APPROVED_DIR, DONE_DIR

logger = logging.getLogger(__name__)

LOCAL_ONLY_TOKENS = ("whatsapp", "payment", "send", "post")


class LocalExecutive:
    def __init__(self, vault_root: Path):
        self.vault_root = vault_root

    def execute_approved(self) -> int:
        """Execute approved items by moving them to Done/Actions.

        This is a placeholder for integration with external executors.
        """
        approved_dir = self.vault_root / APPROVED_DIR
        done_actions = self.vault_root / DONE_DIR / "Actions"
        done_actions.mkdir(parents=True, exist_ok=True)
        if not approved_dir.exists():
            return 0
        count = 0
        for item in approved_dir.glob("*.md"):
            target = done_actions / item.name
            item.replace(target)
            if self._is_local_only(target):
                append_log(
                    self.vault_root,
                    "local_only",
                    f"Local-only action {target.name}",
                    tier="platinum",
                )
            logger.info("Executed approved item %s", target.name)
            append_log(
                self.vault_root,
                "execute",
                f"Approved item {target.name}",
                tier="platinum",
            )
            count += 1
        return count

    def _is_local_only(self, item: Path) -> bool:
        name = item.name.lower()
        return any(token in name for token in LOCAL_ONLY_TOKENS)
