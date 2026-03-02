"""Shared constants for AI Employee agents."""

# Vault folder names
INBOX_DIR = "Inbox"
NEEDS_ACTION_DIR = "Needs_Action"
DONE_DIR = "Done"
PENDING_APPROVAL_DIR = "Pending_Approval"
PLANS_DIR = "Plans"
APPROVED_DIR = "Approved"
REJECTED_DIR = "Rejected"
LOGS_DIR = "Logs"

# File patterns
PLAN_FILE_PREFIX = "PLAN-"
PLAN_FILE_PATTERN = "PLAN-*.md"
DASHBOARD_FILE = "Dashboard.md"
AUDIT_LOG_PREFIX = "audit-"

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

# Priority levels
PRIORITY_HIGH = "high"
PRIORITY_MEDIUM = "medium"
PRIORITY_LOW = "low"

# Tier names
TIER_BRONZE = "bronze"
TIER_SILVER = "silver"
TIER_GOLD = "gold"
