"""Gold Tier data models — Pydantic v2 models for all Gold entities.

Provides runtime validation, serialization, and type safety for all
Gold Tier data structures.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum, unique
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

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
        # inherited Bronze/Silver actions
        "triage",
        "complete",
        "move",
        "create",
        "update_dashboard",
        "error",
    }
)


@unique
class ErrorType(Enum):
    """Classification of API errors for resilience handling."""

    TRANSIENT = "transient"
    LOGIC = "logic"


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
        """Create an entry timestamped to current UTC.
        
        Args:
            action: Action type (must be a valid Gold action).
            source_file: Vault-relative path of the file acted upon.
            details: Human-readable description of the action.
            result: Outcome — success, failure, warning, or skipped.
            rationale: Mandatory explanation for why the action was taken.
            iteration: Ralph Wiggum loop cycle count.
            duration_ms: Execution time in milliseconds.
            
        Returns:
            A new GoldAuditEntry with current UTC timestamp.
        """
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
    def validate_positive_int(cls, v: int, info: Any) -> int:
        """Validate positive integer values."""
        if v <= 0:
            raise ValueError(f"{info.field_name} must be positive")
        return v
    
    @field_validator("idle_sleep_seconds")
    @classmethod
    def validate_positive_float(cls, v: float, info: Any) -> float:
        """Validate positive float values."""
        if v < 0:
            raise ValueError(f"{info.field_name} must be non-negative")
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


class LoopResult(BaseModel):
    """Summary returned when the autonomous loop exits.
    
    Attributes:
        exit_promise_met: Whether exit conditions were satisfied.
        total_iterations: Total iterations executed.
        plans_completed: Number of plans completed.
        plans_blocked: Number of plans blocked.
        tasks_completed: Number of individual tasks completed.
        duration_seconds: Total execution time in seconds.
    """
    
    model_config = ConfigDict(frozen=True)
    
    exit_promise_met: bool
    total_iterations: int
    plans_completed: int
    plans_blocked: int
    tasks_completed: int
    duration_seconds: float
    
    @field_validator("total_iterations", "plans_completed", "plans_blocked", "tasks_completed")
    @classmethod
    def validate_non_negative_int(cls, v: int, info: Any) -> int:
        """Validate non-negative integer values."""
        if v < 0:
            raise ValueError(f"{info.field_name} must be non-negative")
        return v
    
    @field_validator("duration_seconds")
    @classmethod
    def validate_non_negative_float(cls, v: float, info: Any) -> float:
        """Validate non-negative float values."""
        if v < 0:
            raise ValueError(f"{info.field_name} must be non-negative")
        return v


# ---------------------------------------------------------------------------
# Odoo Integration
# ---------------------------------------------------------------------------


class OdooConfig(BaseModel):
    """Odoo JSON-RPC connection settings (loaded from .env).
    
    Attributes:
        url: Odoo server URL (without trailing slash).
        database: Database name.
        username: Username for authentication.
        api_key: API key for authentication (NEVER persisted).
    """
    
    model_config = ConfigDict(frozen=True)
    
    url: str
    database: str
    username: str
    api_key: str
    
    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Validate and normalize URL (remove trailing slash)."""
        if not v or not v.strip():
            raise ValueError("URL cannot be empty")
        return v.strip().rstrip("/")
    
    @field_validator("database", "username", "api_key")
    @classmethod
    def validate_non_empty(cls, v: str, info: Any) -> str:
        """Validate non-empty string values."""
        if not v or not v.strip():
            raise ValueError(f"{info.field_name} cannot be empty")
        return v.strip()


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
    def validate_non_empty(cls, v: str, info: Any) -> str:
        """Validate non-empty string values."""
        if not v or not v.strip():
            raise ValueError(f"{info.field_name} cannot be empty")
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
        json_rpc_payload: Full JSON-RPC payload for the operation.
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
    json_rpc_payload: dict = Field(default_factory=dict)
    
    @field_validator("operation_id", "model", "method")
    @classmethod
    def validate_non_empty(cls, v: str, info: Any) -> str:
        """Validate non-empty string values."""
        if not v or not v.strip():
            raise ValueError(f"{info.field_name} cannot be empty")
        return v.strip()
    
    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        """Validate status is a known value."""
        valid_statuses = {"pending", "executed", "failed", "approved"}
        if v not in valid_statuses:
            raise ValueError(f"Invalid status: {v}. Must be one of {valid_statuses}")
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
        approval_file_path: Path to approval file in vault.
        adapted_versions: Platform-specific content adaptations.
    """
    
    model_config = ConfigDict(frozen=True)
    
    draft_id: str
    platform: str
    content: str
    media_paths: tuple[str, ...] = ()
    scheduled: str = "immediate"
    rationale: str = ""
    approval_status: str = "pending"
    approval_file_path: str = ""
    adapted_versions: dict = Field(default_factory=dict)
    
    @field_validator("draft_id", "platform", "content")
    @classmethod
    def validate_non_empty(cls, v: str, info: Any) -> str:
        """Validate non-empty string values."""
        if not v or not v.strip():
            raise ValueError(f"{info.field_name} cannot be empty")
        return v.strip()
    
    @field_validator("platform")
    @classmethod
    def validate_platform(cls, v: str) -> str:
        """Validate platform is known."""
        valid_platforms = {"X", "Facebook", "Instagram", "Multi"}
        if v not in valid_platforms:
            raise ValueError(f"Invalid platform: {v}. Must be one of {valid_platforms}")
        return v
    
    @field_validator("approval_status")
    @classmethod
    def validate_approval_status(cls, v: str) -> str:
        """Validate approval status."""
        valid_statuses = {"pending", "approved", "rejected"}
        if v not in valid_statuses:
            raise ValueError(f"Invalid status: {v}. Must be one of {valid_statuses}")
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


# ---------------------------------------------------------------------------
# CEO Briefing
# ---------------------------------------------------------------------------


class BriefingConfig(BaseModel):
    """Settings for the CEO Briefing Engine.
    
    Attributes:
        briefing_day: Day of week for briefing (0=Mon, 6=Sun).
        briefing_hour: Hour for briefing generation (24h format).
        revenue_goal: Monthly revenue target.
        bottleneck_threshold_hours: Hours before task is considered bottleneck.
        utilization_threshold_pct: Utilization % below which subscription is flagged.
        overpriced_threshold_pct: % over market rate to flag as overpriced.
    """
    
    model_config = ConfigDict(frozen=True)
    
    briefing_day: int = 6  # 0=Mon, 6=Sun
    briefing_hour: int = 22  # 24h
    revenue_goal: float = 10000.0
    bottleneck_threshold_hours: float = 48.0
    utilization_threshold_pct: float = 30.0
    overpriced_threshold_pct: float = 20.0
    
    @field_validator("briefing_day")
    @classmethod
    def validate_briefing_day(cls, v: int) -> int:
        """Validate day is 0-6."""
        if not 0 <= v <= 6:
            raise ValueError(f"briefing_day must be 0-6, got {v}")
        return v
    
    @field_validator("briefing_hour")
    @classmethod
    def validate_briefing_hour(cls, v: int) -> int:
        """Validate hour is 0-23."""
        if not 0 <= v <= 23:
            raise ValueError(f"briefing_hour must be 0-23, got {v}")
        return v
    
    @field_validator("revenue_goal")
    @classmethod
    def validate_positive_float(cls, v: float) -> float:
        """Validate positive value."""
        if v < 0:
            raise ValueError(f"revenue_goal must be non-negative, got {v}")
        return v


class BottleneckTask(BaseModel):
    """A stale task in /Needs_Action/.
    
    Attributes:
        filename: Task file name.
        age_hours: Age in hours.
        priority: Task priority (P0, P1, P2, P3, CRITICAL, HIGH, MEDIUM, LOW).
        summary: Brief task description.
    """
    
    model_config = ConfigDict(frozen=True)
    
    filename: str
    age_hours: float
    priority: str
    summary: str
    
    @field_validator("filename", "priority", "summary")
    @classmethod
    def validate_non_empty(cls, v: str, info: Any) -> str:
        """Validate non-empty string values."""
        if not v or not v.strip():
            raise ValueError(f"{info.field_name} cannot be empty")
        return v.strip()
    
    @field_validator("age_hours")
    @classmethod
    def validate_non_negative_float(cls, v: float) -> float:
        """Validate non-negative value."""
        if v < 0:
            raise ValueError(f"age_hours must be non-negative, got {v}")
        return v


class SubscriptionFinding(BaseModel):
    """A subscription optimization recommendation.
    
    Attributes:
        service_name: Subscription service name.
        monthly_cost: Monthly cost in USD.
        utilization_pct: Current utilization percentage (if known).
        market_rate: Market rate comparison (if known).
        finding_type: Type of finding (underused, overpriced, unused).
        recommendation: Suggested action.
        potential_savings: Potential monthly savings in USD.
    """
    
    model_config = ConfigDict(frozen=True)
    
    service_name: str
    monthly_cost: float
    utilization_pct: float | None = None
    market_rate: float | None = None
    finding_type: str = "underused"
    recommendation: str = ""
    potential_savings: float = 0.0
    
    @field_validator("service_name")
    @classmethod
    def validate_non_empty(cls, v: str) -> str:
        """Validate non-empty string."""
        if not v or not v.strip():
            raise ValueError("service_name cannot be empty")
        return v.strip()
    
    @field_validator("finding_type")
    @classmethod
    def validate_finding_type(cls, v: str) -> str:
        """Validate finding type."""
        valid_types = {"underused", "overpriced", "unused", "ok"}
        if v not in valid_types:
            raise ValueError(f"Invalid finding_type: {v}. Must be one of {valid_types}")
        return v
    
    @field_validator("monthly_cost", "potential_savings")
    @classmethod
    def validate_non_negative_float(cls, v: float, info: Any) -> float:
        """Validate non-negative value."""
        if v < 0:
            raise ValueError(f"{info.field_name} must be non-negative, got {v}")
        return v


class CEOBriefing(BaseModel):
    """A generated weekly CEO briefing.
    
    Attributes:
        briefing_id: Unique briefing identifier.
        generated_at: ISO-8601 timestamp of generation.
        period_start: Start date of briefing period.
        period_end: End date of briefing period.
        revenue_mtd: Month-to-date revenue (if available).
        revenue_goal: Monthly revenue target.
        revenue_delta_pct: Percentage delta from goal.
        bottleneck_tasks: Tuple of bottleneck tasks.
        subscription_findings: Tuple of subscription findings.
        data_unavailable: List of unavailable data sources.
        output_path: Path to generated briefing file.
    """
    
    model_config = ConfigDict(frozen=True)
    
    briefing_id: str
    generated_at: str
    period_start: str
    period_end: str
    revenue_mtd: float | None = None
    revenue_goal: float = 10000.0
    revenue_delta_pct: float | None = None
    bottleneck_tasks: tuple[BottleneckTask, ...] = ()
    subscription_findings: tuple[SubscriptionFinding, ...] = ()
    data_unavailable: tuple[str, ...] = ()
    output_path: str = ""
    
    @field_validator("briefing_id", "generated_at", "period_start", "period_end")
    @classmethod
    def validate_non_empty(cls, v: str, info: Any) -> str:
        """Validate non-empty string values."""
        if not v or not v.strip():
            raise ValueError(f"{info.field_name} cannot be empty")
        return v.strip()


# ---------------------------------------------------------------------------
# Resilience
# ---------------------------------------------------------------------------


class CircuitBreakerState(BaseModel):
    """Tracks consecutive failures per API for circuit breaker pattern.
    
    Attributes:
        api_name: Name of the API being tracked.
        consecutive_failures: Number of consecutive failures.
        is_open: Whether circuit breaker is open.
        last_failure: ISO-8601 timestamp of last failure.
        last_error: Error message from last failure.
        opened_at: ISO-8601 timestamp when circuit was opened.
    """
    
    api_name: str
    consecutive_failures: int = 0
    is_open: bool = False
    last_failure: str | None = None
    last_error: str | None = None
    opened_at: str | None = None
    
    @field_validator("api_name")
    @classmethod
    def validate_non_empty(cls, v: str) -> str:
        """Validate non-empty string."""
        if not v or not v.strip():
            raise ValueError("api_name cannot be empty")
        return v.strip()
    
    @field_validator("consecutive_failures")
    @classmethod
    def validate_non_negative_int(cls, v: int) -> int:
        """Validate non-negative integer."""
        if v < 0:
            raise ValueError(f"consecutive_failures must be non-negative, got {v}")
        return v
    
    def record_failure(self, error_msg: str, threshold: int = 3) -> None:
        """Record a failure and open circuit if threshold hit.
        
        Args:
            error_msg: Error message from the failure.
            threshold: Number of failures before opening circuit.
        """
        self.consecutive_failures += 1
        self.last_failure = datetime.now(timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
        self.last_error = error_msg
        if self.consecutive_failures >= threshold:
            self.is_open = True
            self.opened_at = self.last_failure
    
    def record_success(self) -> None:
        """Reset circuit breaker on success."""
        self.consecutive_failures = 0
        self.is_open = False
        self.last_failure = None
        self.last_error = None
        self.opened_at = None


class QuarantinedItem(BaseModel):
    """A failed operation that has been quarantined.
    
    Attributes:
        original_filename: Original file name before quarantine.
        quarantined_filename: New file name with quarantine prefix.
        error_type: Type of error (logic_error or system_error).
        http_status: HTTP status code (if applicable).
        error_message: Error message from the failure.
        original_payload: Original operation payload.
        quarantined_at: ISO-8601 timestamp of quarantine.
        alert_created: Whether an alert was created.
        resolution: Resolution notes (if resolved).
    """
    
    model_config = ConfigDict(frozen=True)
    
    original_filename: str
    quarantined_filename: str
    error_type: str
    http_status: int | None = None
    error_message: str = ""
    original_payload: dict = Field(default_factory=dict)
    quarantined_at: str = ""
    alert_created: bool = False
    resolution: str | None = None
    
    @field_validator("original_filename", "quarantined_filename", "error_type")
    @classmethod
    def validate_non_empty(cls, v: str, info: Any) -> str:
        """Validate non-empty string values."""
        if not v or not v.strip():
            raise ValueError(f"{info.field_name} cannot be empty")
        return v.strip()
    
    @field_validator("error_type")
    @classmethod
    def validate_error_type(cls, v: str) -> str:
        """Validate error type."""
        valid_types = {"logic_error", "system_error"}
        if v not in valid_types:
            raise ValueError(f"Invalid error_type: {v}. Must be one of {valid_types}")
        return v
