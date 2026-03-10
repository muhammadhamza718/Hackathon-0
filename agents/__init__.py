"""AI Employee agents package â€” Bronze, Silver, and Gold tier agents."""

from agents.audit_logger import AuditEntry
from agents.complexity_detector import ComplexityLevel, ComplexityResult
from agents.constants import Tier
from agents.dashboard_writer import VaultStatus
from agents.exceptions import AgentError, VaultError, VaultStructureError
from agents.gold.audit_gold import append_gold_log, read_gold_log
from agents.gold.autonomous_loop import AutonomousLoop
from agents.gold.briefing_engine import CEOBriefingEngine
from agents.gold.models import (
    BriefingConfig,
    BottleneckTask,
    CEOBriefing,
    CircuitBreakerState,
    GoldAuditEntry,
    LoopConfig,
    LoopResult,
    LoopState,
    OdooConfig,
    OdooOperation,
    OdooSession,
    PublishResult,
    QuarantinedItem,
    SocialDraft,
    SubscriptionFinding,
)
from agents.gold.odoo_rpc_client import OdooRPCClient, load_odoo_config
from agents.gold.resilient_executor import ResilientExecutor, classify_error
from agents.gold.safety_gate import GoldSafetyGate
from agents.gold.social_bridge import SocialBridge
from agents.hitl_gate import Decision
from agents.inbox_scanner import Priority, ScanResult
from agents.plan_manager import PlanStatus
from agents.plan_parser import PlanSummary
from agents.reconciler import ReconcileResult, ReconcileStrategy
from agents.validators import ValidationResult
from agents.vault_context import vault_session
from agents.vault_init import InitResult
from agents.vault_router import ClassificationResult, TaskClassification
from agents.platinum.claim_manager import ClaimManager
from agents.platinum.cloud_orchestrator import CloudOrchestrator
from agents.platinum.config import PlatinumConfig
from agents.platinum.dashboard_federator import FederatedStatus
from agents.platinum.git_sync_manager import GitSyncManager
from agents.platinum.heartbeat_monitor import HeartbeatMonitor
from agents.platinum.local_executive import LocalExecutive
from agents.platinum.models import ConflictRecord, NodeHeartbeat, NodeRole, NodeStatus, SyncState, TaskClaim
from agents.platinum.odoo_health_monitor import OdooHealthMonitor
__version__ = "0.5.0"
__author__ = "muhammadhamza718"

__all__ = [
    "__version__",
    "__author__",
    # Core enums
    "Tier",
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
    "ReconcileStrategy",
    # HITL
    "Decision",
    # Audit
    "AuditEntry",
    # Vault
    "VaultStatus",
    "ValidationResult",
    "InitResult",
    "vault_session",
    # Gold Tier - Models
    "BriefingConfig",
    "BottleneckTask",
    "CEOBriefing",
    "CircuitBreakerState",
    "GoldAuditEntry",
    "LoopConfig",
    "LoopResult",
    "LoopState",
    "OdooConfig",
    "OdooOperation",
    "OdooSession",
    "PublishResult",
    "QuarantinedItem",
    "SocialDraft",
    "SubscriptionFinding",
    # Gold Tier - Classes
    "AutonomousLoop",
    "CEOBriefingEngine",
    "GoldSafetyGate",
    "OdooRPCClient",
    "ResilientExecutor",
    "SocialBridge",
    # Gold Tier - Functions
    "append_gold_log",
    "read_gold_log",
    "load_odoo_config",
    "classify_error",
    # Platinum Tier
    "CloudOrchestrator",
    "LocalExecutive",
    "GitSyncManager",
    "ClaimManager",
    "HeartbeatMonitor",
    "OdooHealthMonitor",
    "PlatinumConfig",
    "FederatedStatus",
    "NodeHeartbeat",
    "NodeRole",
    "NodeStatus",
    "TaskClaim",
    "SyncState",
    "ConflictRecord",
]

