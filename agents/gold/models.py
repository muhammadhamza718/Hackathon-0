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


# ---------------------------------------------------------------------------
# Ralph Wiggum Loop
# ---------------------------------------------------------------------------


class LoopConfig(BaseModel):
    """Configuration for the Ralph Wiggum autonomous loop.

    Attributes:
        max_iterations: Maximum iterations before forced exit.
        checkpoint_interval: Iterations between state checkpoints.
        idle_sleep_seconds: Seconds to sleep when no work found.
    """

    model_config = ConfigDict(frozen=True)

    max_iterations: int = 1000
    checkpoint_interval: int = 1
    idle_sleep_seconds: float = 5.0

    @field_validator("max_iterations", "checkpoint_interval")
    @classmethod
    def validate_positive_int(cls, v: int) -> int:
        """Validate positive integer values."""
        if v <= 0:
            raise ValueError("Value must be positive")
        return v

    @field_validator("idle_sleep_seconds")
    @classmethod
    def validate_positive_float(cls, v: float) -> float:
        """Validate positive float values."""
        if v < 0:
            raise ValueError("Value must be non-negative")
        return v


class LoopState(BaseModel):
    """Serializable checkpoint for the autonomous loop.

    Attributes:
        session_id: Unique session identifier.
        iteration: Current iteration count.
        active_plan_id: ID of currently executing plan (if any).
        active_step_index: Index of current step in active plan.
        blocked_plans: Tuple of blocked plan IDs.
        last_checkpoint: ISO-8601 timestamp of last checkpoint.
        exit_promise_met: Whether exit conditions are satisfied.
    """

    model_config = ConfigDict(frozen=True)

    session_id: str
    iteration: int = 0
    active_plan_id: str | None = None
    active_step_index: int | None = None
    blocked_plans: tuple[str, ...] = ()
    last_checkpoint: str = ""
    exit_promise_met: bool = False

    @field_validator("session_id")
    @classmethod
    def validate_session_id(cls, v: str) -> str:
        """Validate session ID is non-empty."""
        if not v or not v.strip():
            raise ValueError("Session ID cannot be empty")
        return v.strip()

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dict."""
        return {
            "session_id": self.session_id,
            "iteration": self.iteration,
            "active_plan_id": self.active_plan_id,
            "active_step_index": self.active_step_index,
            "blocked_plans": list(self.blocked_plans),
            "last_checkpoint": self.last_checkpoint,
            "exit_promise_met": self.exit_promise_met,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> LoopState:
        """Deserialize from dict."""
        return cls(
            session_id=data["session_id"],
            iteration=data.get("iteration", 0),
            active_plan_id=data.get("active_plan_id"),
            active_step_index=data.get("active_step_index"),
            blocked_plans=tuple(data.get("blocked_plans", [])),
            last_checkpoint=data.get("last_checkpoint", ""),
            exit_promise_met=data.get("exit_promise_met", False),
        )


# ---------------------------------------------------------------------------
# Odoo Integration
# ---------------------------------------------------------------------------


class OdooSession(BaseModel):
    """Authenticated Odoo session state.

    Attributes:
        url: Odoo server URL.
        database: Database name.
        uid: Authenticated user ID.
        authenticated: Whether session is authenticated.
        last_call: ISO-8601 timestamp of last API call.
    """

    url: str
    database: str
    uid: int = 0
    authenticated: bool = False
    last_call: str | None = None

    @field_validator("url", "database")
    @classmethod
    def validate_non_empty(cls, v: str) -> str:
        """Validate non-empty string values."""
        if not v or not v.strip():
            raise ValueError("Field cannot be empty")
        return v.strip()


class OdooOperation(BaseModel):
    """A pending or completed Odoo RPC call.

    Attributes:
        operation_id: Unique operation identifier.
        model: Odoo model name (e.g., 'account.move').
        method: RPC method (e.g., 'search_read', 'create', 'write').
        args: Positional arguments for the RPC call.
        kwargs: Keyword arguments for the RPC call.
        is_write: Whether this is a write operation.
        requires_approval: Whether HITL approval is required.
        status: Operation status (pending, executed, failed).
        result: Operation result (if completed).
        error: Error message (if failed).
    """

    model_config = ConfigDict(frozen=False)

    operation_id: str
    model: str
    method: str
    args: tuple = ()
    kwargs: dict = Field(default_factory=dict)
    is_write: bool = False
    requires_approval: bool = False
    status: str = "pending"
    result: Any = None
    error: str | None = None

    @field_validator("operation_id", "model", "method")
    @classmethod
    def validate_non_empty(cls, v: str) -> str:
        """Validate non-empty string values."""
        if not v or not v.strip():
            raise ValueError("Field cannot be empty")
        return v.strip()

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        """Validate status is a known value."""
        valid_statuses = {"pending", "executed", "failed", "approved"}
        if v not in valid_statuses:
            raise ValueError(f"Invalid status: {v}")
        return v

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dict."""
        return {
            "operation_id": self.operation_id,
            "model": self.model,
            "method": self.method,
            "args": list(self.args),
            "kwargs": self.kwargs,
            "is_write": self.is_write,
            "requires_approval": self.requires_approval,
            "status": self.status,
            "error": self.error,
        }


# ---------------------------------------------------------------------------
# Social Media
# ---------------------------------------------------------------------------


class SocialDraft(BaseModel):
    """A social media post draft per Constitution XII.

    Attributes:
        draft_id: Unique draft identifier.
        platform: Target platform (X, Facebook, Instagram, Multi).
        content: Post content (already adapted for platform).
        media_paths: Paths to media files to attach.
        scheduled: Scheduling directive (immediate or specific time).
        rationale: Reason for creating this post.
        approval_status: Current approval status.
    """

    model_config = ConfigDict(frozen=True)

    draft_id: str
    platform: str
    content: str
    media_paths: tuple[str, ...] = ()
    scheduled: str = "immediate"
    rationale: str = ""
    approval_status: str = "pending"

    @field_validator("draft_id", "platform", "content")
    @classmethod
    def validate_non_empty(cls, v: str) -> str:
        """Validate non-empty string values."""
        if not v or not v.strip():
            raise ValueError("Field cannot be empty")
        return v.strip()

    @field_validator("platform")
    @classmethod
    def validate_platform(cls, v: str) -> str:
        """Validate platform is known."""
        valid_platforms = {"X", "Facebook", "Instagram", "Multi"}
        if v not in valid_platforms:
            raise ValueError(f"Invalid platform: {v}")
        return v

    @field_validator("approval_status")
    @classmethod
    def validate_approval_status(cls, v: str) -> str:
        """Validate approval status."""
        valid_statuses = {"pending", "approved", "rejected"}
        if v not in valid_statuses:
            raise ValueError(f"Invalid status: {v}")
        return v


class PublishResult(BaseModel):
    """Outcome of publishing an approved social post.

    Attributes:
        success: Whether publication was successful.
        platform: Target platform.
        published_at: ISO-8601 timestamp of publication.
        post_url: URL to the published post (if available).
        error: Error message (if failed).
    """

    model_config = ConfigDict(frozen=True)

    success: bool
    platform: str
    published_at: str = ""
    post_url: str | None = None
    error: str | None = None

    @field_validator("platform")
    @classmethod
    def validate_platform(cls, v: str) -> str:
        """Validate platform is known."""
        if not v or not v.strip():
            raise ValueError("Platform cannot be empty")
        return v.strip()
