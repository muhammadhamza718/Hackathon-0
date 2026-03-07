# Gold Tier Architecture

## Overview

The Gold Tier Autonomous Agent is a self-correcting, persistent Digital FTE (Full-Time Employee) that operates with full autonomy while maintaining strict safety gates for high-risk operations.

## Core Principles

1. **Autonomy with Safety**: Full operational autonomy with HITL (Human-In-The-Loop) approval for high-risk actions
2. **Auditability**: Every action is logged to an immutable audit trail
3. **Resilience**: Automatic retry with exponential backoff and circuit breaker patterns
4. **Persistence**: State checkpoints enable recovery from interruptions
5. **Transparency**: All decisions include rationale documentation

## Architecture Components

```
┌─────────────────────────────────────────────────────────────┐
│                    Gold Tier Agent                          │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │   Ralph     │  │   Safety    │  │      Audit          │  │
│  │  Wiggum     │──│    Gate     │──│      Logger         │  │
│  │   Loop      │  │   (HITL)    │  │                     │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
│         │                │                    │              │
│         ▼                ▼                    ▼              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │  Progress   │  │ Resilient   │  │   Configuration     │  │
│  │  Tracker    │  │  Executor   │  │      Manager        │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              Integration Layer                        │   │
│  ├─────────────┬─────────────┬─────────────────────────┤   │
│  │    Odoo     │   Social    │      Browser            │   │
│  │    RPC      │   Media     │    Automation           │   │
│  │   Client    │   Bridge    │                         │   │
│  └─────────────┴─────────────┴─────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## Key Components

### Ralph Wiggum Loop

The autonomous execution engine that:
- Continuously scans for work in `/Needs_Action/`
- Executes tasks with appropriate safety gates
- Logs all actions to the audit trail
- Self-corrects on failures
- Persists state for recovery

**Exit Conditions:**
- No work found for N consecutive iterations
- Max iterations reached
- Manual interrupt
- Exit promise met

### Safety Gate (HITL)

All high-risk operations require human approval:
- Odoo write operations
- Social media publishing
- Payments over $100
- External communications

Approval requests are stored in `/Pending_Approval/` with full context.

### Audit Logger

Immutable JSON audit log with:
- Timestamp (ISO-8601 UTC)
- Action type
- Rationale (mandatory)
- Result (success/failure/warning/skipped)
- Iteration count
- Duration

### Resilient Executor

Fault-tolerant execution with:
- Exponential backoff retry
- Circuit breaker pattern
- Configurable retry limits
- Execution metrics

### Integration Layer

#### Odoo Integration
- JSON-RPC client for Odoo 19+
- Connection pooling
- MCP server wrapper
- Operation logging with credential redaction

#### Social Media
- Platform adapters (X, Facebook, Instagram)
- Content adaptation per platform
- Image optimization
- Analytics aggregation
- Browser automation for platforms without APIs

#### CEO Briefing Engine
- Revenue MTD vs Goal analysis
- Task bottleneck detection
- Subscription optimization recommendations
- Automated markdown generation

## Data Models

All data models use Pydantic v2 for:
- Runtime validation
- Type safety
- Serialization
- Documentation

Key models:
- `GoldAuditEntry`: Immutable audit record
- `LoopState`: Serializable checkpoint
- `OdooSession`: Authenticated session state
- `SocialDraft`: Platform-adapted content
- `CEOBriefing`: Generated executive summary

## Directory Structure

```
agents/gold/
├── __init__.py              # Package exports
├── models.py                # Pydantic data models
├── exceptions.py            # Exception hierarchy
├── config.py                # Configuration management
├── audit_gold.py            # Audit logger
├── safety_gate.py           # HITL approval gate
├── resilient_executor.py    # Retry and circuit breaker
├── autonomous_loop.py       # Ralph Wiggum Loop
├── progress_tracker.py      # Progress tracking
├── odoo_rpc_client.py       # Odoo JSON-RPC client
├── odoo_mcp_server.py       # Odoo MCP wrapper
├── odoo_connection_pool.py  # Connection pooling
├── social_bridge.py         # Social media adapters
├── social_analytics.py      # Analytics aggregation
├── social_automation.py     # Browser automation
├── image_optimizer.py       # Image compression
├── briefing_engine.py       # CEO briefing generation
├── revenue_analysis.py      # Revenue trend analysis
└── subscription_tracker.py  # Subscription management
```

## Safety Guarantees

1. **No Silent Failures**: All errors are logged and reported
2. **No Unauthorized Actions**: High-risk actions require HITL
3. **No Data Loss**: State checkpoints enable recovery
4. **No Infinite Loops**: Max iterations and idle detection
5. **No Credential Exposure**: Credentials never logged or persisted

## Operational Modes

### Development Mode
- Verbose logging
- Relaxed rate limits
- Local Odoo instance

### Production Mode
- Structured JSON logging
- Strict rate limits
- Production Odoo instance
- Enhanced monitoring

## Monitoring

Key metrics to track:
- Loop iteration success rate
- Average iteration duration
- HITL approval turnaround time
- Circuit breaker status
- Queue depth (/Needs_Action/ count)

## Extension Points

The architecture supports extension through:
1. **Work Handlers**: Register custom work source scanners
2. **Exit Conditions**: Register custom exit criteria
3. **Platform Adapters**: Add new social media platforms
4. **Analysis Modules**: Add new briefing analysis types

## Version History

- **v0.1.0**: Initial Gold Tier implementation
- Core loop, safety gate, audit logger
- Odoo integration
- Social media bridge
- CEO briefing engine
