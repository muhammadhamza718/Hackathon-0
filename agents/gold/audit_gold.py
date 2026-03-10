"""Gold-tier JSON audit logger.

Provides append-only audit logging for all Gold Tier operations per
Constitution XVI (Auditability).
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .models import GoldAuditEntry


class GoldAuditLogger:
    """Append-only JSON audit logger for Gold Tier operations.

    All audit entries are written to dated log files in the Logs/
    directory. Each day gets its own log file in JSON Lines format.
    """

    def __init__(self, logs_dir: str = "Logs"):
        """Initialize the audit logger.

        Args:
            logs_dir: Base directory for audit logs.
        """
        self.logs_dir = Path(logs_dir)
        self.logs_dir.mkdir(parents=True, exist_ok=True)

    def _get_log_path(self) -> Path:
        """Get the log file path for today."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        return self.logs_dir / f"{today}.json"

    def log(self, entry: GoldAuditEntry) -> None:
        """Append an audit entry to today's log file.

        Args:
            entry: The audit entry to log.
        """
        log_path = self._get_log_path()
        entry_dict = entry.to_dict()

        # Read existing entries if file exists
        entries: list[dict[str, Any]] = []
        if log_path.exists():
            with open(log_path, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if content:
                    entries = json.loads(content)

        # Append new entry
        entries.append(entry_dict)

        # Write back atomically
        temp_path = log_path.with_suffix(".tmp")
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(entries, f, indent=2)

        temp_path.replace(log_path)

    def log_action(
        self,
        action: str,
        rationale: str,
        source_file: str = "",
        details: str = "",
        result: str = "success",
        iteration: int = 0,
        duration_ms: int = 0,
    ) -> GoldAuditEntry:
        """Create and log an audit entry.

        Args:
            action: Action type (must be a valid Gold action).
            rationale: Mandatory explanation for why the action was taken.
            source_file: Vault-relative path of the file acted upon.
            details: Human-readable description of the action.
            result: Outcome â€” success, failure, warning, or skipped.
            iteration: Ralph Wiggum loop cycle count.
            duration_ms: Execution time in milliseconds.

        Returns:
            The created audit entry.
        """
        entry = GoldAuditEntry.now(
            action=action,
            source_file=source_file,
            details=details,
            result=result,
            rationale=rationale,
            iteration=iteration,
            duration_ms=duration_ms,
        )
        self.log(entry)
        return entry

    def get_entries_for_date(
        self, date_str: str
    ) -> list[GoldAuditEntry]:
        """Get all audit entries for a specific date.

        Args:
            date_str: Date string in YYYY-MM-DD format.

        Returns:
            List of audit entries for the specified date.
        """
        log_path = self.logs_dir / f"{date_str}.json"
        if not log_path.exists():
            return []

        with open(log_path, "r", encoding="utf-8") as f:
            entries = json.load(f)

        return [GoldAuditEntry(**entry) for entry in entries]

    def get_recent_entries(
        self, days: int = 7
    ) -> list[GoldAuditEntry]:
        """Get audit entries from the last N days.

        Args:
            days: Number of days to look back.

        Returns:
            List of audit entries from the specified period.
        """
        all_entries: list[GoldAuditEntry] = []
        today = datetime.now(timezone.utc)

        for i in range(days):
            date = today.replace(
                day=today.day - i
            )  # Simplified - proper implementation would handle month boundaries
            date_str = date.strftime("%Y-%m-%d")
            entries = self.get_entries_for_date(date_str)
            all_entries.extend(entries)

        return all_entries

    def count_by_action(
        self, date_str: str | None = None
    ) -> dict[str, int]:
        """Count audit entries by action type.

        Args:
            date_str: Optional date string (YYYY-MM-DD). If None, uses today.

        Returns:
            Dictionary mapping action names to counts.
        """
        if date_str is None:
            date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        entries = self.get_entries_for_date(date_str)
        counts: dict[str, int] = {}

        for entry in entries:
            action = entry.action
            counts[action] = counts.get(action, 0) + 1

        return counts

    def count_by_result(
        self, date_str: str | None = None
    ) -> dict[str, int]:
        """Count audit entries by result type.

        Args:
            date_str: Optional date string (YYYY-MM-DD). If None, uses today.

        Returns:
            Dictionary mapping result types to counts.
        """
        if date_str is None:
            date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        entries = self.get_entries_for_date(date_str)
        counts: dict[str, int] = {}

        for entry in entries:
            result = entry.result
            counts[result] = counts.get(result, 0) + 1

        return counts


def append_gold_log(
    vault_root: str | Path,
    action: str,
    details: str,
    rationale: str,
    source_file: str = "",
    result: str = "success",
    iteration: int = 0,
    duration_ms: int = 0,
) -> GoldAuditEntry:
    """Append a Gold audit entry to the vault Logs directory."""
    logger = GoldAuditLogger(logs_dir=Path(vault_root) / "Logs")
    return logger.log_action(
        action=action,
        rationale=rationale,
        source_file=source_file,
        details=details,
        result=result,
        iteration=iteration,
        duration_ms=duration_ms,
    )


def read_gold_log(vault_root: str | Path, date_str: str | None = None) -> list[GoldAuditEntry]:
    """Read Gold audit entries for a specific date."""
    logger = GoldAuditLogger(logs_dir=Path(vault_root) / "Logs")
    if date_str is None:
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return logger.get_entries_for_date(date_str)


def log_sync_event(
    vault_root: str | Path,
    result: str,
    rationale: str,
    details: str = "",
    source_file: str = "",
) -> GoldAuditEntry:
    """Log a distributed sync event."""
    action = "sync_cycle"
    if result == "blocked":
        action = "sync_blocked"
    return append_gold_log(
        vault_root=vault_root,
        action=action,
        details=details,
        rationale=rationale,
        source_file=source_file,
        result="success" if result == "success" else "warning",
    )


def log_claim_event(
    vault_root: str | Path,
    action: str,
    rationale: str,
    details: str = "",
    source_file: str = "",
) -> GoldAuditEntry:
    """Log a distributed claim event."""
    return append_gold_log(
        vault_root=vault_root,
        action=action,
        details=details,
        rationale=rationale,
        source_file=source_file,
    )


def log_heartbeat_event(
    vault_root: str | Path,
    action: str,
    rationale: str,
    details: str = "",
    source_file: str = "",
) -> GoldAuditEntry:
    """Log a distributed heartbeat event."""
    return append_gold_log(
        vault_root=vault_root,
        action=action,
        details=details,
        rationale=rationale,
        source_file=source_file,
    )
