"""AI Employee agents package — Bronze, Silver, and Gold tier agents."""

from agents.exceptions import AgentError, VaultError, VaultStructureError
from agents.inbox_scanner import Priority, ScanResult
from agents.reconciler import ReconcileResult
from agents.vault_context import vault_session
from agents.vault_router import ClassificationResult, TaskClassification

__version__ = "0.3.0"
__author__ = "muhammadhamza718"

__all__ = [
    "__version__",
    "__author__",
    # Core types
    "AgentError",
    "VaultError",
    "VaultStructureError",
    # Classification
    "TaskClassification",
    "ClassificationResult",
    # Inbox
    "Priority",
    "ScanResult",
    # Reconciliation
    "ReconcileResult",
    # Context management
    "vault_session",
]
