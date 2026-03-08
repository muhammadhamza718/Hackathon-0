"""Gold Tier autonomous employee modules.

This package provides full autonomy capabilities for the AI Digital FTE,
including Odoo accounting integration, social media management, CEO briefing
generation, and the Ralph Wiggum autonomous execution loop.

## Modules

- **autonomous_loop**: Ralph Wiggum persistent execution loop
- **briefing_engine**: CEO weekly briefing generation
- **briefing_templates**: Customizable briefing templates
- **config**: Gold Tier configuration settings
- **image_optimizer**: Image validation and compression
- **models**: Pydantic v2 data models
- **odoo_connection_pool**: Odoo JSON-RPC connection management
- **odoo_logger**: Odoo operation audit logging
- **odoo_mcp_server**: Odoo MCP server wrapper
- **odoo_rpc_client**: Odoo JSON-RPC client
- **resilient_executor**: Circuit breaker and retry logic
- **safety_gate**: HITL approval gating
- **social_bridge**: Multi-platform social media management
- **social_automation**: Browser MCP posting automation

## Usage Example

```python
from agents.gold import SocialBridge, CEOBriefingEngine
from pathlib import Path

vault = Path("/path/to/vault")

# Social media posting
bridge = SocialBridge(vault)
draft = bridge.draft_post(
    platform="X",
    content="Hello world!",
    optimize_emojis=True,
    include_hashtags=True,
)

# CEO briefing
engine = CEOBriefingEngine(vault)
briefing = engine.generate_briefing_with_trends()
```

## Safety Gates

All external actions route through HITL approval:
- Social posts → `/Pending_Approval/`
- Financial > $100 → `/Pending_Approval/`
- External emails → `/Pending_Approval/`
"""

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

__all__ = [
    # Models
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
]
