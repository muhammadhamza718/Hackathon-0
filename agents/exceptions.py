"""Custom exception classes for the AI Employee agent system."""

from __future__ import annotations

__all__ = [
    "AgentError",
    "VaultError",
    "VaultStructureError",
    "FileRoutingError",
    "PlanError",
    "PlanNotFoundError",
    "PlanValidationError",
    "HITLError",
    "ApprovalTimeoutError",
    "ReconciliationError",
    "ConfigurationError",
    "ScanError",
    "TemplateError",
    # Gold Tier
    "OdooError",
    "OdooAuthError",
    "SocialMediaError",
    "ContentValidationError",
    "BriefingError",
    "CircuitOpenError",
    "QuarantineError",
    "TransientAPIError",
    "LogicAPIError",
    "ApprovalNotFoundError",
    # Gold Tier Loop exceptions
    "LoopExitError",
    "CheckpointError",
    "StateCorruptionError",
]


class AgentError(Exception):
    """Base exception for all agent errors."""

    @property
    def short_name(self) -> str:
        """Return the unqualified class name for logging."""
        return type(self).__name__


class VaultError(AgentError):
    """Error related to vault operations."""


class VaultStructureError(VaultError):
    """Vault is missing required directories."""


class FileRoutingError(VaultError):
    """Error while routing a file between vault folders."""


class PlanError(AgentError):
    """Error related to plan operations."""


class PlanNotFoundError(PlanError):
    """Requested plan file does not exist."""


class PlanValidationError(PlanError):
    """Plan file failed validation (bad frontmatter, missing fields)."""


class HITLError(AgentError):
    """Error related to HITL approval gate."""


class ApprovalTimeoutError(HITLError):
    """Approval request timed out without human response."""


class ReconciliationError(AgentError):
    """Error during session reconciliation."""


class ConfigurationError(AgentError):
    """Invalid or missing configuration."""


class ScanError(AgentError):
    """Error during inbox or vault scanning."""


class TemplateError(AgentError):
    """Error while rendering a task template."""


# ---------------------------------------------------------------------------
# Gold Tier exceptions
# ---------------------------------------------------------------------------


class OdooError(AgentError):
    """Error communicating with Odoo via JSON-RPC."""


class OdooAuthError(OdooError):
    """Odoo authentication failed."""


class SocialMediaError(AgentError):
    """Error during social media operations."""


class ContentValidationError(SocialMediaError):
    """Social post content exceeds platform limits."""


class BriefingError(AgentError):
    """Error generating a CEO briefing."""


class CircuitOpenError(AgentError):
    """Call rejected because the circuit breaker is open."""

    def __init__(self, api_name: str) -> None:
        super().__init__(f"Circuit breaker open for '{api_name}'")
        self.api_name = api_name


class QuarantineError(AgentError):
    """Error during quarantine operation."""


class TransientAPIError(AgentError):
    """Transient API error (retryable): 429, 5xx, timeouts."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class LogicAPIError(AgentError):
    """Logic API error (not retryable): 400, 401, 403, 422."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class ApprovalNotFoundError(HITLError):
    """Expected file in /Approved/ but it was not found."""


# ---------------------------------------------------------------------------
# Gold Tier Loop exceptions
# ---------------------------------------------------------------------------


class LoopExitError(AgentError):
    """Ralph Wiggum loop exited unexpectedly or with errors.
    
    Attributes:
        reason: Explanation for why the loop exited.
        iterations_completed: Number of iterations completed before exit.
        exit_promise_met: Whether exit promise was satisfied.
    """
    
    def __init__(
        self,
        reason: str,
        iterations_completed: int = 0,
        exit_promise_met: bool = False,
    ) -> None:
        super().__init__(f"Loop exited: {reason}")
        self.reason = reason
        self.iterations_completed = iterations_completed
        self.exit_promise_met = exit_promise_met


class CheckpointError(AgentError):
    """Error during loop state checkpointing.
    
    Attributes:
        message: Error message describing the checkpoint failure.
        state_path: Path to the checkpoint file (if known).
        original_exception: Original exception that caused the failure.
    """
    
    def __init__(
        self,
        message: str,
        state_path: str | None = None,
        original_exception: Exception | None = None,
    ) -> None:
        super().__init__(message)
        self.state_path = state_path
        self.original_exception = original_exception


class StateCorruptionError(AgentError):
    """Loop state file is corrupted and cannot be recovered.
    
    Attributes:
        state_path: Path to the corrupted state file.
        corruption_type: Type of corruption detected.
        recovery_suggestion: Suggested recovery action.
    """
    
    def __init__(
        self,
        state_path: str,
        corruption_type: str = "unknown",
        recovery_suggestion: str = "Manual intervention required",
    ) -> None:
        super().__init__(
            f"State corruption detected at {state_path}: {corruption_type}. "
            f"Suggestion: {recovery_suggestion}"
        )
        self.state_path = state_path
        self.corruption_type = corruption_type
        self.recovery_suggestion = recovery_suggestion
