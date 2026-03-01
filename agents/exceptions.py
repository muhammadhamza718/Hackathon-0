"""Custom exception classes for the AI Employee agent system."""

from __future__ import annotations


class AgentError(Exception):
    """Base exception for all agent errors."""


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
