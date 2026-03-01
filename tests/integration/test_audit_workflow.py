"""Integration test: audit logging through vault operations."""

from __future__ import annotations

from pathlib import Path

import pytest

from agents.audit_logger import append_log, read_log
from agents.hitl_gate import HITLGate
from agents.vault_router import route_file


@pytest.fixture
def vault(tmp_path: Path) -> Path:
    for d in ("Inbox", "Needs_Action", "Done", "Pending_Approval",
              "Approved", "Rejected", "Logs"):
        (tmp_path / d).mkdir()
    return tmp_path


class TestAuditedRouting:
    """Verify that routing + audit logging work together."""

    def test_simple_route_logged(self, vault: Path):
        task = vault / "Inbox" / "fix.md"
        task.write_text("# Fix a bug\n\nSimple fix.")

        dest = route_file(task, vault)
        append_log(vault, "route", f"Routed {task.name} to {dest.parent.name}")

        log = read_log(vault)
        assert "route" in log
        assert "fix.md" in log

    def test_hitl_submit_logged(self, vault: Path):
        task = vault / "Inbox" / "email.md"
        task.write_text("# Send email\n\nEmail the report.")

        dest = route_file(task, vault)
        append_log(vault, "route", f"Routed to {dest.parent.name}", tier="silver")

        gate = HITLGate(vault)
        pending = gate.get_pending()
        assert len(pending) == 1

        log = read_log(vault)
        assert "[silver]" in log


class TestAuditLogIntegrity:
    """Verify audit log append-only behavior."""

    def test_multiple_operations(self, vault: Path):
        append_log(vault, "start", "Session started")
        append_log(vault, "route", "Routed task-1")
        append_log(vault, "approve", "Approved task-2")
        append_log(vault, "complete", "Marked task-1 done")

        log = read_log(vault)
        lines = [l for l in log.splitlines() if l.startswith("- [")]
        assert len(lines) == 4
