"""Centralized configuration for Gold Tier.

Provides constants and configuration management for all Gold Tier operations.
"""

import os
from dataclasses import dataclass
from typing import Final


# ---------------------------------------------------------------------------
# Environment Variables
# ---------------------------------------------------------------------------

ENV_PREFIX: Final[str] = "GOLD_"


@dataclass(frozen=True)
class OdooConfig:
    """Odoo JSON-RPC connection settings."""

    url: str
    database: str
    username: str
    api_key: str

    @classmethod
    def from_env(cls) -> "OdooConfig":
        """Load Odoo configuration from environment variables."""
        return cls(
            url=os.getenv("ODOO_URL", "http://localhost:8069"),
            database=os.getenv("ODOO_DATABASE", "odoo"),
            username=os.getenv("ODOO_USERNAME", "admin"),
            api_key=os.getenv("ODOO_API_KEY", ""),
        )


@dataclass(frozen=True)
class LoopConfig:
    """Ralph Wiggum autonomous loop configuration."""

    max_iterations: int = 1000
    checkpoint_interval: int = 1
    idle_sleep_seconds: float = 5.0
    max_concurrent_plans: int = 5

    @classmethod
    def from_env(cls) -> "LoopConfig":
        """Load loop configuration from environment variables."""
        return cls(
            max_iterations=int(os.getenv("GOLD_MAX_ITERATIONS", "1000")),
            checkpoint_interval=int(os.getenv("GOLD_CHECKPOINT_INTERVAL", "1")),
            idle_sleep_seconds=float(os.getenv("GOLD_IDLE_SLEEP_SECONDS", "5.0")),
            max_concurrent_plans=int(os.getenv("GOLD_MAX_CONCURRENT_PLANS", "5")),
        )


@dataclass(frozen=True)
class BriefingConfig:
    """CEO Briefing Engine configuration."""

    briefing_day: int = 0  # Monday
    briefing_hour: int = 8  # 8 AM
    revenue_goal: float = 10000.0
    bottleneck_threshold_hours: float = 48.0

    @classmethod
    def from_env(cls) -> "BriefingConfig":
        """Load briefing configuration from environment variables."""
        return cls(
            briefing_day=int(os.getenv("GOLD_BRIEFING_DAY", "0")),
            briefing_hour=int(os.getenv("GOLD_BRIEFING_HOUR", "8")),
            revenue_goal=float(os.getenv("GOLD_REVENUE_GOAL", "10000.0")),
            bottleneck_threshold_hours=float(
                os.getenv("GOLD_BOTTLENECK_THRESHOLD_HOURS", "48.0")
            ),
        )


@dataclass(frozen=True)
class ResilienceConfig:
    """Resilience and retry configuration."""

    max_retries: int = 3
    base_delay_seconds: float = 1.0
    max_delay_seconds: float = 60.0
    exponential_base: float = 2.0
    circuit_breaker_threshold: int = 3
    circuit_breaker_reset_seconds: float = 30.0

    @classmethod
    def from_env(cls) -> "ResilienceConfig":
        """Load resilience configuration from environment variables."""
        return cls(
            max_retries=int(os.getenv("GOLD_MAX_RETRIES", "3")),
            base_delay_seconds=float(os.getenv("GOLD_BASE_DELAY_SECONDS", "1.0")),
            max_delay_seconds=float(os.getenv("GOLD_MAX_DELAY_SECONDS", "60.0")),
            exponential_base=float(os.getenv("GOLD_EXPONENTIAL_BASE", "2.0")),
            circuit_breaker_threshold=int(
                os.getenv("GOLD_CIRCUIT_BREAKER_THRESHOLD", "3")
            ),
            circuit_breaker_reset_seconds=float(
                os.getenv("GOLD_CIRCUIT_BREAKER_RESET_SECONDS", "30.0")
            ),
        )


@dataclass(frozen=True)
class SafetyConfig:
    """HITL safety gate configuration."""

    hitl_timeout_seconds: float = 3600.0  # 1 hour
    approval_required_actions: frozenset[str] = frozenset(
        {
            "odoo_write",
            "odoo_create",
            "odoo_delete",
            "social_post",
            "payment_over_100",
        }
    )

    @classmethod
    def from_env(cls) -> "SafetyConfig":
        """Load safety configuration from environment variables."""
        return cls(
            hitl_timeout_seconds=float(
                os.getenv("GOLD_HITL_TIMEOUT_SECONDS", "3600.0")
            ),
        )


# ---------------------------------------------------------------------------
# Vault Paths (relative to project root)
# ---------------------------------------------------------------------------

VAULT_INBOX: Final[str] = "Inbox"
VAULT_NEEDS_ACTION: Final[str] = "Needs_Action"
VAULT_PENDING_APPROVAL: Final[str] = "Pending_Approval"
VAULT_DONE: Final[str] = "Done"
VAULT_LOGS: Final[str] = "Logs"
VAULT_BRIEFINGS: Final[str] = "Briefings"


# ---------------------------------------------------------------------------
# Platform Constants
# ---------------------------------------------------------------------------

SOCIAL_PLATFORMS: Final[frozenset[str]] = frozenset(
    {"X", "Facebook", "Instagram", "Multi"}
)

PLATFORM_CHAR_LIMITS: Final[dict[str, int]] = {
    "X": 280,
    "Facebook": 63206,
    "Instagram": 2200,
}


# ---------------------------------------------------------------------------
# Audit Constants
# ---------------------------------------------------------------------------

AUDIT_LOG_FORMAT: Final[str] = "json"
AUDIT_RETENTION_DAYS: Final[int] = 90
