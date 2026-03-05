"""AI Employee agents package — Bronze, Silver, and Gold tier agents."""

from agents.audit_logger import AuditEntry
from agents.complexity_detector import ComplexityLevel, ComplexityResult
from agents.dashboard_writer import VaultStatus
from agents.exceptions import AgentError, VaultError, VaultStructureError
from agents.hitl_gate import Decision
from agents.inbox_scanner import Priority, ScanResult
from agents.plan_manager import PlanStatus
from agents.plan_parser import PlanSummary
from agents.reconciler import ReconcileResult
from agents.validators import ValidationResult
from agents.vault_context import vault_session
from agents.vault_init import InitResult
from agents.vault_router import ClassificationResult, TaskClassification

__version__ = "0.4.0"
__author__ = "muhammadhamza718"

__all__ = [
    "__version__",
    "__author__",
    # Exceptions
    "AgentError",
    "VaultError",
    "VaultStructureError",
    # Classification
    "TaskClassification",
    "ClassificationResult",
    "ComplexityLevel",
    "ComplexityResult",
    # Inbox & Priority
    "Priority",
    "ScanResult",
    # Plans
    "PlanStatus",
    "PlanSummary",
    # Reconciliation
    "ReconcileResult",
    # HITL
    "Decision",
    # Audit
    "AuditEntry",
    # Vault
    "VaultStatus",
    "ValidationResult",
    "InitResult",
    "vault_session",
]
