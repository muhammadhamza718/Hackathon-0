"""
AuditLogger: JSON-based audit trail for all Silver Tier plan operations.

Appends structured JSON log entries to /Logs/YYYY-MM-DD.json, providing
a tamper-evident, human-readable audit trail of every plan lifecycle event.

Log events tracked:
  - plan_created       : New Plan.md created
  - step_completed     : A roadmap step marked [x]
  - approval_drafted   : Approval request written to /Pending_Approval/
  - approval_executed  : External action dispatched via MCP
  - approval_rejected  : Human moved file to /Rejected/
  - plan_archived      : Plan moved to /Done/Plans/
  - plan_corrupted     : Plan quarantined due to parse failure
  - plan_consolidated  : Duplicate merged into primary
  - mcp_failure        : MCP call failed and file returned to /Pending_Approval/

Log file format: /Logs/YYYY-MM-DD.json
  - One JSON object per line (newline-delimited JSON / NDJSON).
  - Each entry: timestamp, event, actor, plan_id, step_id, result, detail.

Usage:
    audit = AuditLogger(vault_root=Path("/vault"))
    audit.log(event="plan_created", plan_id="2026-001", detail="Invoice workflow")
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Recognised event types (open set — unknown events are still logged)
KNOWN_EVENTS = frozenset({
    "plan_created",
    "step_completed",
    "approval_drafted",
    "approval_executed",
    "approval_rejected",
    "plan_archived",
    "plan_corrupted",
    "plan_consolidated",
    "mcp_failure",
})


class AuditLogger:
    """
    Appends NDJSON audit entries to /Logs/YYYY-MM-DD.json.

    Each entry is a single JSON object on its own line, making logs
    both machine-readable and easily grep-able.
    """

    ACTOR = "Agent"

    def __init__(self, vault_root: Path) -> None:
        """
        Args:
            vault_root: Root directory of the Obsidian vault.
        """
        self.logs_dir = vault_root / "Logs"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def log(
        self,
        event: str,
        plan_id: str,
        *,
        step_id: Optional[int] = None,
        result: str = "success",
        detail: str = "",
        actor: Optional[str] = None,
    ) -> None:
        """
        Append a structured audit entry to today's log file.

        Args:
            event:    One of KNOWN_EVENTS or any custom string.
            plan_id:  Identifier of the plan being acted upon.
            step_id:  Step number within the plan (None if not step-specific).
            result:   "success" | "failure" | "warning" (default "success").
            detail:   Human-readable description of what happened.
            actor:    Who/what performed the action (default "Agent").
        """
        if event not in KNOWN_EVENTS:
            logger.warning("Unknown audit event type '%s' — logging anyway", event)

        entry = {
            "timestamp": self._iso_timestamp(),
            "event": event,
            "actor": actor or self.ACTOR,
            "plan_id": plan_id,
            "step_id": step_id,
            "result": result,
            "detail": detail,
        }

        log_path = self._today_log_path()
        self._append_entry(log_path, entry)

    # ------------------------------------------------------------------
    # Convenience wrappers — map directly to tracked event types
    # ------------------------------------------------------------------

    def plan_created(self, plan_id: str, objective: str) -> None:
        self.log("plan_created", plan_id, detail=f"Objective: {objective}")

    def step_completed(self, plan_id: str, step_id: int, description: str) -> None:
        self.log("step_completed", plan_id, step_id=step_id,
                 detail=f"Step {step_id} completed: {description}")

    def approval_drafted(
        self,
        plan_id: str,
        step_id: int,
        action_type: str,
        filename: str,
    ) -> None:
        self.log(
            "approval_drafted",
            plan_id,
            step_id=step_id,
            detail=f"action_type={action_type}, file={filename}",
        )

    def approval_executed(
        self,
        plan_id: str,
        step_id: int,
        action_type: str,
        filename: str,
    ) -> None:
        self.log(
            "approval_executed",
            plan_id,
            step_id=step_id,
            detail=f"action_type={action_type}, file={filename}",
        )

    def approval_rejected(self, plan_id: str, step_id: int, filename: str) -> None:
        self.log(
            "approval_rejected",
            plan_id,
            step_id=step_id,
            result="warning",
            detail=f"file={filename}",
        )

    def plan_archived(self, plan_id: str) -> None:
        self.log("plan_archived", plan_id, detail="Moved to /Done/Plans/")

    def plan_corrupted(self, plan_id: str, quarantine_path: str) -> None:
        self.log(
            "plan_corrupted",
            plan_id,
            result="failure",
            detail=f"Quarantined to {quarantine_path}",
        )

    def plan_consolidated(self, primary_id: str, duplicate_id: str) -> None:
        self.log(
            "plan_consolidated",
            primary_id,
            detail=f"Duplicate {duplicate_id} merged and archived",
        )

    def mcp_failure(
        self,
        plan_id: str,
        step_id: int,
        filename: str,
        error: str,
    ) -> None:
        self.log(
            "mcp_failure",
            plan_id,
            step_id=step_id,
            result="failure",
            detail=f"file={filename}, error={error}",
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _today_log_path(self) -> Path:
        """Return path for today's log file: /Logs/YYYY-MM-DD.json"""
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        return self.logs_dir / f"{date_str}.json"

    def _append_entry(self, log_path: Path, entry: dict) -> None:
        """Append a single JSON entry (NDJSON line) to the log file."""
        log_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with log_path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
            logger.debug("Audit entry written: event=%s plan=%s", entry["event"], entry["plan_id"])
        except OSError as exc:
            # Log failure must never crash the main workflow
            logger.error("Failed to write audit log entry to %s: %s", log_path, exc)

    @staticmethod
    def _iso_timestamp() -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
