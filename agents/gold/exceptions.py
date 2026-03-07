"""Gold-tier specific exception types.

Provides structured exception handling for Gold Tier operations including
Odoo integration, social media management, and CEO briefing generation.
"""

from __future__ import annotations


class GoldTierError(Exception):
    """Base exception for all Gold Tier errors."""

    pass


class OdooIntegrationError(GoldTierError):
    """Base exception for Odoo integration errors."""

    pass


class OdooConnectionError(OdooIntegrationError):
    """Raised when Odoo connection fails."""

    pass


class OdooAuthenticationError(OdooIntegrationError):
    """Raised when Odoo authentication fails."""

    pass


class OdooOperationError(OdooIntegrationError):
    """Raised when an Odoo operation fails."""

    def __init__(self, operation: str, message: str, model: str | None = None):
        self.operation = operation
        self.model = model
        super().__init__(f"{operation} failed: {message}")


class SocialMediaError(GoldTierError):
    """Base exception for social media errors."""

    pass


class SocialDraftError(SocialMediaError):
    """Raised when social draft creation fails."""

    pass


class SocialPublishError(SocialMediaError):
    """Raised when social post publishing fails."""

    pass


class BriefingError(GoldTierError):
    """Base exception for CEO briefing errors."""

    pass


class BriefingGenerationError(BriefingError):
    """Raised when briefing generation fails."""

    pass


class LoopError(GoldTierError):
    """Base exception for Ralph Wiggum loop errors."""

    pass


class LoopExitError(LoopError):
    """Raised when loop exits unexpectedly."""

    pass


class LoopIterationError(LoopError):
    """Raised when loop iteration fails."""

    pass


class ResilienceError(GoldTierError):
    """Base exception for resilience handling errors."""

    pass


class CircuitBreakerOpenError(ResilienceError):
    """Raised when circuit breaker is open."""

    def __init__(self, api_name: str, message: str = "Circuit breaker is open"):
        self.api_name = api_name
        super().__init__(f"{api_name}: {message}")


class MaxRetriesExceededError(ResilienceError):
    """Raised when max retries exceeded."""

    pass


class SafetyGateError(GoldTierError):
    """Base exception for safety gate errors."""

    pass


class HITLTimeoutError(SafetyGateError):
    """Raised when HITL approval times out."""

    pass


class AuditError(GoldTierError):
    """Base exception for audit logging errors."""

    pass
