"""Gold Tier data models — frozen dataclasses for all Gold entities."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum, unique

from agents.constants import TIER_GOLD

# ---------------------------------------------------------------------------
# Gold-specific action types
# ---------------------------------------------------------------------------

GOLD_ACTIONS = frozenset(
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


@dataclass(frozen=True)
class GoldAuditEntry:
    """Immutable Gold-tier audit entry per Constitution XVI."""

    timestamp: str
    action: str
    source_file: str
    details: str
    result: str
    rationale: str
    iteration: int
    tier: str = TIER_GOLD
    duration_ms: int = 0

    def to_dict(self) -> dict:
        """Serialize to a JSON-compatible dict."""
        return {
            "timestamp": self.timestamp,
            "action": self.action,
            "source_file": self.source_file,
            "details": self.details,
            "result": self.result,
            "rationale": self.rationale,
            "iteration": self.iteration,
            "tier": self.tier,
            "duration_ms": self.duration_ms,
        }

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


@dataclass(frozen=True)
class LoopConfig:
    """Configuration for the Ralph Wiggum autonomous loop."""

    max_iterations: int = 1000
    checkpoint_interval: int = 1
    idle_sleep_seconds: float = 5.0


@dataclass(frozen=True)
class LoopState:
    """Serializable checkpoint for the autonomous loop."""

    session_id: str
    iteration: int = 0
    active_plan_id: str | None = None
    active_step_index: int | None = None
    blocked_plans: tuple[str, ...] = ()
    last_checkpoint: str = ""
    exit_promise_met: bool = False

    def to_dict(self) -> dict:
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
    def from_dict(cls, data: dict) -> LoopState:
        return cls(
            session_id=data["session_id"],
            iteration=data.get("iteration", 0),
            active_plan_id=data.get("active_plan_id"),
            active_step_index=data.get("active_step_index"),
            blocked_plans=tuple(data.get("blocked_plans", [])),
            last_checkpoint=data.get("last_checkpoint", ""),
            exit_promise_met=data.get("exit_promise_met", False),
        )


@dataclass(frozen=True)
class LoopResult:
    """Summary returned when the autonomous loop exits."""

    exit_promise_met: bool
    total_iterations: int
    plans_completed: int
    plans_blocked: int
    tasks_completed: int
    duration_seconds: float


# ---------------------------------------------------------------------------
# Odoo Integration
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class OdooConfig:
    """Odoo JSON-RPC connection settings (loaded from .env)."""

    url: str
    database: str
    username: str
    api_key: str  # NEVER persisted to vault files


@dataclass
class OdooSession:
    """Authenticated Odoo session state."""

    url: str
    database: str
    uid: int = 0
    authenticated: bool = False
    last_call: str | None = None

    # api_key intentionally NOT stored here — kept only in OdooConfig


@dataclass(frozen=True)
class OdooOperation:
    """A pending or completed Odoo RPC call."""

    operation_id: str
    model: str
    method: str
    args: tuple = ()
    kwargs: dict = field(default_factory=dict)
    is_write: bool = False
    requires_approval: bool = False
    status: str = "pending"
    result: object = None
    error: str | None = None
    json_rpc_payload: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
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


@dataclass(frozen=True)
class SocialDraft:
    """A social media post draft per Constitution XII."""

    draft_id: str
    platform: str  # X | Facebook | Instagram | Multi
    content: str
    media_paths: tuple[str, ...] = ()
    scheduled: str = "immediate"
    rationale: str = ""
    approval_status: str = "pending"
    approval_file_path: str = ""
    adapted_versions: dict = field(default_factory=dict)


@dataclass(frozen=True)
class PublishResult:
    """Outcome of publishing an approved social post."""

    success: bool
    platform: str
    published_at: str = ""
    post_url: str | None = None
    error: str | None = None


# ---------------------------------------------------------------------------
# CEO Briefing
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BriefingConfig:
    """Settings for the CEO Briefing Engine."""

    briefing_day: int = 6  # 0=Mon, 6=Sun
    briefing_hour: int = 22  # 24h
    revenue_goal: float = 10000.0
    bottleneck_threshold_hours: float = 48.0
    utilization_threshold_pct: float = 30.0
    overpriced_threshold_pct: float = 20.0


@dataclass(frozen=True)
class BottleneckTask:
    """A stale task in /Needs_Action/."""

    filename: str
    age_hours: float
    priority: str
    summary: str


@dataclass(frozen=True)
class SubscriptionFinding:
    """A subscription optimization recommendation."""

    service_name: str
    monthly_cost: float
    utilization_pct: float | None = None
    market_rate: float | None = None
    finding_type: str = "underused"  # underused | overpriced | unused
    recommendation: str = ""
    potential_savings: float = 0.0


@dataclass(frozen=True)
class CEOBriefing:
    """A generated weekly CEO briefing."""

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


# ---------------------------------------------------------------------------
# Resilience
# ---------------------------------------------------------------------------


@dataclass
class CircuitBreakerState:
    """Tracks consecutive failures per API for circuit breaker pattern."""

    api_name: str
    consecutive_failures: int = 0
    is_open: bool = False
    last_failure: str | None = None
    last_error: str | None = None
    opened_at: str | None = None

    def record_failure(self, error_msg: str, threshold: int = 3) -> None:
        """Record a failure and open circuit if threshold hit."""
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


@dataclass(frozen=True)
class QuarantinedItem:
    """A failed operation that has been quarantined."""

    original_filename: str
    quarantined_filename: str
    error_type: str  # logic_error | system_error
    http_status: int | None = None
    error_message: str = ""
    original_payload: dict = field(default_factory=dict)
    quarantined_at: str = ""
    alert_created: bool = False
    resolution: str | None = None
