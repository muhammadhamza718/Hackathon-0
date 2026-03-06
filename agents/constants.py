"""Shared constants for AI Employee agents."""

from enum import Enum, unique


@unique
class Tier(Enum):
    """Agent capability tiers."""

    BRONZE = "bronze"
    SILVER = "silver"
    GOLD = "gold"

    @property
    def can_use_hitl(self) -> bool:
        """True when the tier supports human-in-the-loop gates."""
        return self in (Tier.SILVER, Tier.GOLD)

    @property
    def can_act_externally(self) -> bool:
        """True when the tier can perform external actions (with approval)."""
        return self is Tier.GOLD


# Vault folder names
INBOX_DIR = "Inbox"
NEEDS_ACTION_DIR = "Needs_Action"
DONE_DIR = "Done"
PENDING_APPROVAL_DIR = "Pending_Approval"
PLANS_DIR = "Plans"
APPROVED_DIR = "Approved"
REJECTED_DIR = "Rejected"
LOGS_DIR = "Logs"
ARCHIVE_DIR = "Archive"

# File patterns
PLAN_FILE_PREFIX = "PLAN-"
PLAN_FILE_PATTERN = "PLAN-*.md"
DASHBOARD_FILE = "Dashboard.md"
AUDIT_LOG_PREFIX = "audit-"
COMPANY_HANDBOOK_FILE = "Company_Handbook.md"

# Plan statuses
STATUS_DRAFT = "draft"
STATUS_ACTIVE = "active"
STATUS_BLOCKED = "blocked"
STATUS_COMPLETE = "complete"
STATUS_APPROVED = "approved"
STATUS_REJECTED = "rejected"
STATUS_CANCELLED = "cancelled"

# HITL markers
HITL_MARKER = "✋"
STEP_DONE_MARKER = "[x]"
STEP_PENDING_MARKER = "[ ]"
REASONING_LOG_PREFIX = "## Reasoning Logs"

# Priority levels
PRIORITY_CRITICAL = "critical"
PRIORITY_HIGH = "high"
PRIORITY_MEDIUM = "medium"
PRIORITY_LOW = "low"

# Default config
DEFAULT_STABILITY_SECONDS = 2.0
MAX_INBOX_SCAN_FILES = 100
DEFAULT_LOG_LEVEL = "INFO"
DEFAULT_ALLOWED_EXTENSIONS = ".md,.txt,.pdf,.jpg,.jpeg,.png"
HITL_TIMEOUT_SECONDS = 3600  # 1 hour

# Tier names
TIER_BRONZE = "bronze"
TIER_SILVER = "silver"
TIER_GOLD = "gold"

# Gold Tier: loop state file
LOOP_STATE_FILE = "loop-state.json"

# Gold Tier: file prefixes
BRIEFING_PREFIX = "CEO-Briefing-"
QUARANTINE_PREFIX = "[QUARANTINED]_"

# Gold Tier: HITL thresholds
PAYMENT_APPROVAL_THRESHOLD = 100.0

# Gold Tier: resilience defaults
MAX_RETRIES = 5
BACKOFF_BASE_SECONDS = 1.0
BACKOFF_MAX_SECONDS = 60.0
CIRCUIT_BREAKER_THRESHOLD = 3

# Gold Tier: valid Gold audit actions
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
        # inherited
        "triage",
        "complete",
        "move",
        "create",
        "update_dashboard",
        "error",
    }
)
