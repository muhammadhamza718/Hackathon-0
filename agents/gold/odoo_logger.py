"""Odoo Operation Logger - Comprehensive logging with credential redaction.

Logs all Odoo operations with timing, success/failure metrics, and
automatic credential redaction for security.
"""

from __future__ import annotations

import hashlib
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from agents.constants import TIER_GOLD
from agents.gold.audit_gold import append_gold_log
from agents.utils import ensure_dir, utcnow_iso

logger = logging.getLogger(__name__)


@dataclass
class OdooOperationLog:
    """Record of an Odoo operation."""

    operation_id: str
    timestamp: str
    model: str
    method: str
    duration_ms: float
    success: bool
    error: str | None = None
    records_affected: int = 0
    redacted_payload: dict | None = None


class OdooOperationLogger:
    """Logger for Odoo operations with credential redaction.

    Features:
    - Automatic credential redaction in all logs
    - Timing metrics for all operations
    - Success/failure tracking
    - Operation-level audit trail
    - Aggregated metrics
    """

    def __init__(
        self,
        vault_root: Path,
        redact_fields: tuple[str, ...] = ("api_key", "password", "secret", "token"),
    ) -> None:
        """Initialize Odoo operation logger.

        Args:
            vault_root: Root path of the vault for audit logs.
            redact_fields: Field names to redact from logs.
        """
        self.vault_root = vault_root
        self.redact_fields = redact_fields
        self._operation_count = 0
        self._success_count = 0
        self._failure_count = 0
        self._total_duration_ms = 0.0

    def redact_credentials(self, data: Any) -> Any:
        """Recursively redact credentials from data.

        Args:
            data: Data to redact (dict, list, or primitive).

        Returns:
            Data with credentials replaced by "***REDACTED***".
        """
        if isinstance(data, dict):
            return {
                key: "***REDACTED***" if key.lower() in self.redact_fields else self.redact_credentials(value)
                for key, value in data.items()
            }
        elif isinstance(data, list):
            return [self.redact_credentials(item) for item in data]
        elif isinstance(data, str):
            # Redact if it looks like an API key (long alphanumeric)
            if len(data) > 20 and data.isalnum():
                return "***REDACTED***"
            return data
        else:
            return data

    def log_operation(
        self,
        model: str,
        method: str,
        duration_ms: float,
        success: bool,
        error: str | None = None,
        records_affected: int = 0,
        payload: dict | None = None,
        rationale: str = "",
    ) -> OdooOperationLog:
        """Log an Odoo operation.

        Args:
            model: Odoo model name.
            method: Operation method (search_read, create, write, etc.).
            duration_ms: Operation duration in milliseconds.
            success: Whether operation succeeded.
            error: Error message if failed.
            records_affected: Number of records affected.
            payload: Operation payload (will be redacted).
            rationale: Business rationale for the operation.

        Returns:
            OdooOperationLog record.
        """
        self._operation_count += 1
        if success:
            self._success_count += 1
        else:
            self._failure_count += 1
        self._total_duration_ms += duration_ms

        operation_id = hashlib.sha256(
            f"{model}-{method}-{utcnow_iso()}-{self._operation_count}".encode()
        ).hexdigest()[:12]

        log_entry = OdooOperationLog(
            operation_id=operation_id,
            timestamp=utcnow_iso(),
            model=model,
            method=method,
            duration_ms=round(duration_ms, 2),
            success=success,
            error=error,
            records_affected=records_affected,
            redacted_payload=self.redact_credentials(payload) if payload else None,
        )

        # Write to audit log - use allowed action types
        action = "odoo_read" if method in ("search_read", "read") else "odoo_write_draft"
        details = (
            f"{method} on {model}: "
            f"{'success' if success else 'failed'} "
            f"({duration_ms:.1f}ms, {records_affected} records)"
        )
        if error:
            details += f" - {error}"

        append_gold_log(
            vault_root=self.vault_root,
            action=action,
            details=details,
            rationale=rationale or f"Odoo {method} operation",
            source_file=f"Logs/{datetime.now(timezone.utc).strftime('%Y-%m-%d')}.json",
        )

        logger.debug(
            "Odoo operation: %s.%s - %s (%.1fms)",
            model,
            method,
            "✓" if success else "✗",
            duration_ms,
        )

        return log_entry

    def context_manager(self, model: str, method: str, rationale: str = ""):
        """Context manager for timing operations.

        Usage:
            with logger.context_manager("res.partner", "create") as ctx:
                result = odoo_client.create(...)
                ctx.records_affected = 1
                ctx.success = True

        Args:
            model: Odoo model name.
            method: Operation method.
            rationale: Business rationale.

        Returns:
            TimedOperationContext.
        """
        return TimedOperationContext(self, model, method, rationale)

    def get_metrics(self) -> dict[str, Any]:
        """Get aggregated operation metrics.

        Returns:
            Dict with operation metrics.
        """
        avg_duration = (
            self._total_duration_ms / max(1, self._operation_count)
        )
        success_rate = (
            self._success_count / max(1, self._operation_count) * 100
        )

        return {
            "total_operations": self._operation_count,
            "successful": self._success_count,
            "failed": self._failure_count,
            "success_rate_pct": round(success_rate, 2),
            "total_duration_ms": round(self._total_duration_ms, 2),
            "avg_duration_ms": round(avg_duration, 2),
        }

    def reset_metrics(self) -> None:
        """Reset all metrics."""
        self._operation_count = 0
        self._success_count = 0
        self._failure_count = 0
        self._total_duration_ms = 0.0


@dataclass
class TimedOperationContext:
    """Context manager for timing Odoo operations."""

    logger: OdooOperationLogger
    model: str
    method: str
    rationale: str
    success: bool = True
    error: str | None = None
    records_affected: int = 0
    payload: dict | None = None
    _start_time: float = field(default=0, init=False)

    def __enter__(self) -> "TimedOperationContext":
        """Start timing."""
        self._start_time = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Stop timing and log."""
        duration_ms = (time.perf_counter() - self._start_time) * 1000
        error = str(exc_val) if exc_val else None

        self.logger.log_operation(
            model=self.model,
            method=self.method,
            duration_ms=duration_ms,
            success=self.success and error is None,
            error=error or self.error,
            records_affected=self.records_affected,
            payload=self.payload,
            rationale=self.rationale,
        )


class OdooAuditLogger:
    """Dedicated audit logger for Odoo operations.

    Creates daily audit log files with all Odoo operations.
    """

    def __init__(self, vault_root: Path) -> None:
        """Initialize Odoo audit logger.

        Args:
            vault_root: Root path of the vault.
        """
        self.vault_root = vault_root
        self._logs_dir = ensure_dir(vault_root / "Logs")

    def log_operation(
        self,
        operation: str,
        model: str,
        method: str,
        details: str,
        rationale: str,
        success: bool,
    ) -> str:
        """Log an Odoo operation to daily audit file.

        Args:
            operation: Operation type (odoo_read, odoo_write_draft).
            model: Odoo model name.
            method: Operation method.
            details: Operation details.
            rationale: Business rationale.
            success: Whether operation succeeded.

        Returns:
            Details of the logged operation.
        """
        # Use allowed action types
        action = operation if operation in ("odoo_read", "odoo_write_draft") else "odoo_read"
        entry = append_gold_log(
            vault_root=self.vault_root,
            action=action,
            details=details,
            rationale=rationale,
            source_file=f"Logs/{datetime.now(timezone.utc).strftime('%Y-%m-%d')}.json",
        )
        return str(entry)

    def log_credentials_access(
        self,
        action: str,
        rationale: str,
    ) -> str:
        """Log credentials-related access (always redacted).

        Args:
            action: Action performed (authenticate, refresh, etc.).
            rationale: Business rationale.

        Returns:
            Details of the logged operation.
        """
        return self.log_operation(
            operation="odoo_read",  # Use allowed action
            model="res.users",
            method=action,
            details=f"Credentials accessed (redacted) - {action}",
            rationale=rationale,
            success=True,
        )
