"""Cloud orchestrator for Platinum distributed perception."""

from __future__ import annotations

import logging
from pathlib import Path

from agents.constants import INBOX_DIR, NEEDS_ACTION_DIR, UPDATES_DIR
from agents.platinum.heartbeat_monitor import HeartbeatMonitor
from agents.platinum.models import NodeRole
from agents.platinum.odoo_health_monitor import OdooHealthMonitor
from agents.platinum.utils import resolve_node_id

logger = logging.getLogger(__name__)

LOCAL_ONLY_TOKENS = ("whatsapp", "payment", "approved", "send", "post")


class CloudOrchestrator:
    def __init__(self, vault_root: Path):
        self.vault_root = vault_root
        self.node_id = resolve_node_id()
        self.heartbeat = HeartbeatMonitor(vault_root, self.node_id, role=NodeRole.CLOUD)
        self.odoo_monitor = OdooHealthMonitor()

    def run_cycle(self) -> dict[str, int]:
        """Perform one perception cycle: triage inbox, publish heartbeat."""
        triaged = self._triage_inbox()
        odoo_status = self.odoo_monitor.heartbeat().status
        self.heartbeat.publish(odoo_status=odoo_status)
        return {"triaged": triaged}

    def _triage_inbox(self) -> int:
        inbox = self.vault_root / INBOX_DIR
        if not inbox.exists():
            return 0
        needs_action = self.vault_root / NEEDS_ACTION_DIR
        needs_action.mkdir(parents=True, exist_ok=True)
        count = 0
        for item in inbox.glob("*.md"):
            if self._is_local_only(item):
                self._defer_to_local(item)
                continue
            target = needs_action / item.name
            item.replace(target)
            count += 1
        return count

    def _is_local_only(self, item: Path) -> bool:
        name = item.name.lower()
        return any(token in name for token in LOCAL_ONLY_TOKENS)

    def _defer_to_local(self, item: Path) -> None:
        updates_dir = self.vault_root / UPDATES_DIR / "deferred"
        updates_dir.mkdir(parents=True, exist_ok=True)
        target = updates_dir / item.name
        item.replace(target)
        logger.info("Deferred local-only item %s", item.name)

    def create_odoo_draft(self, title: str, details: str) -> Path:
        """Create an approval-ready accounting draft for Local review."""
        pending = self.vault_root / "Pending_Approval"
        pending.mkdir(parents=True, exist_ok=True)
        filename = f"odoo-draft-{title.replace(' ', '-').lower()}.md"
        path = pending / filename
        body = [
            f"# Odoo Draft: {title}",
            "",
            "Status: draft",
            "",
            "## Details",
            details,
            "",
            "> Move to /Approved/ for Local execution.",
        ]
        path.write_text("\n".join(body), encoding="utf-8")
        return path
