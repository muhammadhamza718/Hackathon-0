"""Gold Tier configuration constants.

Centralized configuration for all Gold Tier components.
All values can be overridden via environment variables or runtime config.
"""

from __future__ import annotations

import os
from typing import Final

# ---------------------------------------------------------------------------
# Ralph Wiggum Loop Configuration
# ---------------------------------------------------------------------------

#: Maximum iterations before forced loop exit
MAX_LOOP_ITERATIONS: Final[int] = int(os.getenv("MAX_LOOP_ITERATIONS", "1000"))

#: Iterations between state checkpoints
LOOP_CHECKPOINT_INTERVAL: Final[int] = int(os.getenv("LOOP_CHECKPOINT_INTERVAL", "1"))

#: Seconds to sleep when no work found
LOOP_IDLE_SLEEP_SECONDS: Final[float] = float(os.getenv("LOOP_IDLE_SLEEP_SECONDS", "5.0"))

# ---------------------------------------------------------------------------
# Odoo Integration Configuration
# ---------------------------------------------------------------------------

#: Odoo JSON-RPC request timeout in seconds
ODOO_TIMEOUT: Final[int] = int(os.getenv("ODOO_TIMEOUT", "30"))

#: Maximum retries for transient Odoo errors
ODOO_MAX_RETRIES: Final[int] = int(os.getenv("ODOO_MAX_RETRIES", "3"))

#: Odoo session pool size (for future connection pooling)
ODOO_POOL_SIZE: Final[int] = int(os.getenv("ODOO_POOL_SIZE", "5"))

# ---------------------------------------------------------------------------
# Social Media Configuration
# ---------------------------------------------------------------------------

#: Platform-specific content limits
SOCIAL_PLATFORM_LIMITS: Final[dict[str, dict]] = {
    "X": {"max_text": 280, "max_images": 4, "max_hashtags": 3},
    "Facebook": {"max_text": 63206, "max_images": 10, "max_hashtags": 30},
    "Instagram": {"max_text": 2200, "max_images": 10, "max_hashtags": 30},
}

#: Default hashtags for different content types
SOCIAL_DEFAULT_HASHTAGS: Final[dict[str, list[str]]] = {
    "general": ["#Business", "#AI", "#Automation"],
    "product": ["#Product", "#Launch", "#Innovation"],
    "engagement": ["#Community", "#Discussion", "#Feedback"],
}

# ---------------------------------------------------------------------------
# CEO Briefing Configuration
# ---------------------------------------------------------------------------

#: Day of week for briefing (0=Monday, 6=Sunday)
BRIEFING_DAY: Final[int] = int(os.getenv("BRIEFING_DAY", "6"))

#: Hour for briefing generation (24h format)
BRIEFING_HOUR: Final[int] = int(os.getenv("BRIEFING_HOUR", "22"))

#: Default monthly revenue goal
REVENUE_GOAL: Final[float] = float(os.getenv("REVENUE_GOAL", "10000.0"))

#: Hours before task is considered a bottleneck
BOTTLENECK_THRESHOLD_HOURS: Final[float] = float(
    os.getenv("BOTTLENECK_THRESHOLD_HOURS", "48.0")
)

#: Utilization % below which subscription is flagged
SUBSCRIPTION_UTILIZATION_THRESHOLD: Final[float] = float(
    os.getenv("SUBSCRIPTION_UTILIZATION_THRESHOLD", "30.0")
)

# ---------------------------------------------------------------------------
# Resilience Configuration
# ---------------------------------------------------------------------------

#: Base delay for exponential backoff (seconds)
BACKOFF_BASE_SECONDS: Final[float] = 1.0

#: Maximum backoff delay (seconds)
BACKOFF_MAX_SECONDS: Final[float] = 60.0

#: Circuit breaker failure threshold
CIRCUIT_BREAKER_THRESHOLD: Final[int] = 3

#: Maximum retries for transient errors
MAX_RETRIES: Final[int] = 3

# ---------------------------------------------------------------------------
# HITL Configuration
# ---------------------------------------------------------------------------

#: Payment approval threshold in USD
PAYMENT_APPROVAL_THRESHOLD: Final[float] = float(
    os.getenv("PAYMENT_APPROVAL_THRESHOLD", "100.00")
)

# ---------------------------------------------------------------------------
# Audit Logging Configuration
# ---------------------------------------------------------------------------

#: Include request/response sizes in audit logs
AUDIT_LOG_PAYLOAD_SIZES: Final[bool] = os.getenv(
    "AUDIT_LOG_PAYLOAD_SIZES", "false"
).lower() in {"true", "1", "yes"}

#: Redact sensitive fields in audit logs
AUDIT_REDACT_SENSITIVE: Final[bool] = True
