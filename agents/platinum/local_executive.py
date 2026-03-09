"""Local-only execution router for Platinum."""

from __future__ import annotations

from pathlib import Path
import logging

from agents.constants import APPROVED_DIR, DONE_DIR

logger = logging.getLogger(__name__)


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
            logger.info("Executed approved item %s", item.name)
            count += 1
        return count
