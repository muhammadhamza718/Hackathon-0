"""Gold Tier Autonomous Agent Package.

This package provides the Gold Tier autonomous agent capabilities including:
- Odoo accounting integration (JSON-RPC)
- Cross-platform social media management
- CEO briefing generation
- Ralph Wiggum autonomous loop
"""

__version__ = "0.1.0"
__author__ = "muhammadhamza718"

from .audit_gold import GoldAuditLogger
from .autonomous_loop import LoopMetrics, LoopResult, RalphWiggumLoop
from .progress_tracker import ProgressReport, ProgressSnapshot, ProgressTracker
from .config import (
    BriefingConfig,
    LoopConfig as LoopConfigData,
    OdooConfig as OdooConfigData,
    ResilienceConfig,
    SafetyConfig,
)
from .odoo_connection_pool import OdooConnectionPool, SessionManager
from .odoo_mcp_server import OdooMCPServer
from .odoo_rpc_client import OdooRPCClient
from .resilient_executor import ExecutionResult, ResilientExecutor
from .safety_gate import ApprovalRequest, GoldSafetyGate
from .social_bridge import (
    FacebookAdapter,
    InstagramAdapter,
    PlatformAdapter,
    SocialBridge,
    XAdapter,
)
from .image_optimizer import ImageOptimizer
from .social_analytics import (
    AnalyticsAggregator,
    AnalyticsSummary,
    PlatformMetrics,
    PostMetrics,
)
from .social_automation import (
    BrowserConfig,
    BrowserMCPTools,
    PublishTask,
    SocialMediaAutomation,
)
from .briefing_engine import CEOBriefingEngine, RevenueData
from .revenue_analysis import (
    PeriodComparison,
    RevenueAnalyzer,
    RevenuePoint,
    RevenueTrend,
)
from .subscription_tracker import (
    MarketComparison,
    Subscription,
    SubscriptionTracker,
    SubscriptionUsage,
)
from .exceptions import (
    AuditError,
    BriefingError,
    CircuitBreakerOpenError,
    GoldTierError,
    HITLTimeoutError,
    LoopError,
    MaxRetriesExceededError,
    OdooAuthenticationError,
    OdooConnectionError,
    OdooIntegrationError,
    OdooOperationError,
    ResilienceError,
    SafetyGateError,
    SocialDraftError,
    SocialMediaError,
    SocialPublishError,
)
from .models import (
    GoldAuditEntry,
    LoopConfig,
    LoopState,
    OdooOperation,
    OdooSession,
    PublishResult,
    SocialDraft,
)

__all__ = [
    # Audit
    "GoldAuditLogger",
    # Loop
    "RalphWiggumLoop",
    "LoopResult",
    "LoopMetrics",
    "ProgressTracker",
    "ProgressReport",
    "ProgressSnapshot",
    # Config
    "OdooConfigData",
    "LoopConfigData",
    "BriefingConfig",
    "ResilienceConfig",
    "SafetyConfig",
    # Odoo
    "OdooRPCClient",
    "OdooMCPServer",
    "OdooConnectionPool",
    "SessionManager",
    # Resilience
    "ResilientExecutor",
    "ExecutionResult",
    # Safety
    "GoldSafetyGate",
    "ApprovalRequest",
    # Social
    "SocialBridge",
    "PlatformAdapter",
    "XAdapter",
    "FacebookAdapter",
    "InstagramAdapter",
    "ImageOptimizer",
    "AnalyticsAggregator",
    "AnalyticsSummary",
    "PlatformMetrics",
    "PostMetrics",
    # Automation
    "SocialMediaAutomation",
    "BrowserMCPTools",
    "BrowserConfig",
    "PublishTask",
    # Briefing
    "CEOBriefingEngine",
    "RevenueData",
    # Revenue Analysis
    "RevenueAnalyzer",
    "RevenuePoint",
    "RevenueTrend",
    "PeriodComparison",
    # Subscription
    "SubscriptionTracker",
    "Subscription",
    "SubscriptionUsage",
    "MarketComparison",
    # Exceptions
    "GoldTierError",
    "OdooIntegrationError",
    "OdooConnectionError",
    "OdooAuthenticationError",
    "OdooOperationError",
    "SocialMediaError",
    "SocialDraftError",
    "SocialPublishError",
    "BriefingError",
    "BriefingGenerationError",
    "LoopError",
    "LoopExitError",
    "LoopIterationError",
    "ResilienceError",
    "CircuitBreakerOpenError",
    "MaxRetriesExceededError",
    "SafetyGateError",
    "HITLTimeoutError",
    "AuditError",
    # Models
    "GoldAuditEntry",
    "LoopConfig",
    "LoopState",
    "OdooOperation",
    "OdooSession",
    "PublishResult",
    "SocialDraft",
    "__version__",
    "__author__",
]
