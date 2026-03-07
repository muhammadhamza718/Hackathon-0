"""Gold Tier data models — Pydantic v2 models for all Gold entities.

Provides runtime validation, serialization, and type safety for all
Gold Tier data structures.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import unique
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from agents.constants import TIER_GOLD

# ---------------------------------------------------------------------------
# Gold-specific action types
# ---------------------------------------------------------------------------

GOLD_ACTIONS: frozenset[str] = frozenset(
    {
        "odoo_read",
        "odoo_write_draft",
        "social_draft",
        "social_post",
        "ceo_briefing",
        "subscription_audit",
        "circuit_breaker",
        "retry",
        "quarantine",
        "triage",
        "complete",
        "move",
        "create",
        "update_dashboard",
        "error",
    }
)


# ---------------------------------------------------------------------------
# Audit
# ---------------------------------------------------------------------------


class GoldAuditEntry(BaseModel):
    """Immutable Gold-tier audit entry per Constitution XVI.

    Attributes:
        timestamp: ISO-8601 UTC timestamp of the action.
        action: Action type (must be a valid Gold action).
        source_file: Vault-relative path of the file acted upon.
        details: Human-readable description of the action.
        result: Outcome — success, failure, warning, or skipped.
        rationale: Mandatory explanation for why the action was taken.
        iteration: Ralph Wiggum loop cycle count.
        tier: Tier identifier (default: "gold").
        duration_ms: Execution time in milliseconds.
    """

    model_config = ConfigDict(frozen=True)

    timestamp: str
    action: str
    source_file: str = ""
    details: str = ""
    result: str = "success"
    rationale: str
    iteration: int = 0
    tier: str = TIER_GOLD
    duration_ms: int = 0

    @field_validator("timestamp")
    @classmethod
    def validate_timestamp(cls, v: str) -> str:
        """Validate timestamp is ISO-8601 format."""
        if v:
            try:
                datetime.fromisoformat(v.replace("Z", "+00:00"))
            except ValueError as exc:
                raise ValueError(f"Invalid timestamp format: {v}") from exc
        return v

    @field_validator("action")
    @classmethod
    def validate_action(cls, v: str) -> str:
        """Validate action is a known Gold action."""
        if v not in GOLD_ACTIONS:
            raise ValueError(f"Unknown action: {v}. Must be one of {GOLD_ACTIONS}")
        return v

    @field_validator("rationale")
    @classmethod
    def validate_rationale(cls, v: str) -> str:
        """Validate rationale is non-empty."""
        if not v or not v.strip():
            raise ValueError("Rationale cannot be empty")
        return v.strip()

    @field_validator("result")
    @classmethod
    def validate_result(cls, v: str) -> str:
        """Validate result is a known outcome."""
        valid_results = {"success", "failure", "warning", "skipped"}
        if v not in valid_results:
            raise ValueError(f"Invalid result: {v}. Must be one of {valid_results}")
        return v

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-compatible dict."""
        return self.model_dump()

    @classmethod
    def now(
        cls,
        *,
        action: str,
        source_file: str = "",
        details: str = "",
        result: str = "success",
        rationale: str,
        iteration: int = 0,
        duration_ms: int = 0,
    ) -> GoldAuditEntry:
        """Create an entry timestamped to current UTC."""
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        return cls(
            timestamp=ts,
            action=action,
            source_file=source_file,
            details=details,
            result=result,
            rationale=rationale,
            iteration=iteration,
            duration_ms=duration_ms,
        )
