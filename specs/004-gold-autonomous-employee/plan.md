# Implementation Plan: Gold Tier Autonomous Employee

**Branch**: `004-gold-autonomous-employee` | **Date**: 2026-03-05 | **Spec**: [specs/004-gold-autonomous-employee/spec.md](../004-gold-autonomous-employee/spec.md)
**Input**: Feature specification from `/specs/004-gold-autonomous-employee/spec.md`

## Summary

Architect and implement a high-autonomy digital employee system that extends the existing Silver Tier (plan management, reconciliation, HITL gating) with six Gold-tier capabilities: persistent autonomous execution (Ralph Wiggum loop), Odoo 19+ accounting via JSON-RPC, multi-platform social media management via Browser MCP, automated CEO briefings, resilient operations with exponential backoff/circuit breaker, and comprehensive audit trailing with mandatory rationale mapping. Every feature maps to a discrete Agent Skill.

## Technical Context

**Language/Version**: Python 3.11+ (existing codebase standard)
**Primary Dependencies**: `requests` (Odoo JSON-RPC), `python-dotenv` (config), `pydantic` (validation) — all new deps must be minimal. Browser MCP client via existing MCP protocol.
**Storage**: Local vault (Obsidian Markdown + JSON in `/Logs/`). Odoo Community 19+ for accounting data (external, via JSON-RPC). No new databases.
**Testing**: pytest (existing). Coverage target: 70% (existing `pyproject.toml` threshold).
**Target Platform**: Windows/Linux/Mac (cross-platform, existing constraint)
**Project Type**: Single project with modular `agents/gold/` package extending existing `agents/`
**Performance Goals**: <5s per loop iteration, <30s Odoo round-trip, <5s dashboard rebuild
**Constraints**: 100% local-first (vault is sole persistent store). Zero PII leakage. All secrets in `.env`. All Gold features as Agent Skills.
**Scale/Scope**: Single-user autonomous employee. 1 Odoo instance, 3 social platforms, weekly briefings.

## Constitution Check

_GATE: Must pass before Phase 0 research. Re-check after Phase 1 design._

- **Bronze/Silver Compliance**: ✅ Passes. All existing Bronze (vault ops, audit logging) and Silver (Plan.md loops, HITL gating, reconciliation-first) principles preserved. No Bronze/Silver rules violated.
- **Gold Tier Autonomy Check**: ✅ Requires Ralph Wiggum loop (Constitution X). Exit promise: `all plans COMPLETE AND /Needs_Action/ empty`. Checkpoint after every iteration to `/Logs/loop-state.json`.
- **HITL Verification**: ✅ Three HITL triggers identified:
  1. Payments >$100 → `/Pending_Approval/` (Constitution XV)
  2. ALL social media posts → `/Pending_Approval/` (Constitution XII, XV)
  3. ALL Odoo write operations (journal entries, reconciliations) → `/Pending_Approval/` (Constitution XI)

**Post-Phase-1 Re-check**: ✅ Data models and contracts align with Constitution. No violations detected. Complexity justified in tracking table below.

## Project Structure

### Documentation (this feature)

```text
specs/004-gold-autonomous-employee/
├── plan.md              # This file
├── research.md          # Phase 0: 7 research decisions
├── data-model.md        # Phase 1: 8 new entities + relationships
├── quickstart.md        # Phase 1: setup and usage guide
├── contracts/
│   ├── autonomous-loop.md   # Ralph Wiggum loop contract
│   ├── odoo-rpc.md          # Odoo JSON-RPC contract
│   ├── social-bridge.md     # Social media contract
│   ├── ceo-briefing.md      # CEO briefing contract
│   └── resilient-executor.md # Resilience contract
└── tasks.md             # Phase 2 (/sp.tasks — NOT created by /sp.plan)
```

### Source Code (repository root)

```text
agents/
├── __init__.py              # Existing — add gold exports
├── gold/                    # NEW — Gold Tier package
│   ├── __init__.py
│   ├── autonomous_loop.py   # Ralph Wiggum persistent loop
│   ├── odoo_rpc_client.py   # Odoo 19+ JSON-RPC adapter
│   ├── social_bridge.py     # Multi-platform social management
│   ├── briefing_engine.py   # CEO briefing generation
│   ├── resilient_executor.py # Exponential backoff + circuit breaker
│   ├── audit_gold.py        # Gold-tier audit logger (extends existing)
│   ├── safety_gate.py       # Gold-tier HITL gate ($100, social posts)
│   └── models.py            # Gold-tier data models (Pydantic/dataclasses)
├── constants.py             # Existing — add Gold action types, tier name
├── exceptions.py            # Existing — add Gold-specific exceptions
├── plan_manager.py          # Existing — no changes needed
├── reconciler.py            # Existing — no changes needed
├── hitl_gate.py             # Existing — extended by gold/safety_gate.py
└── audit_logger.py          # Existing — extended by gold/audit_gold.py

tests/
├── unit/
│   ├── test_gold_autonomous_loop.py
│   ├── test_gold_odoo_rpc.py
│   ├── test_gold_social_bridge.py
│   ├── test_gold_briefing_engine.py
│   ├── test_gold_resilient_executor.py
│   ├── test_gold_audit.py
│   └── test_gold_safety_gate.py
├── integration/
│   ├── test_gold_loop_lifecycle.py
│   ├── test_gold_odoo_integration.py
│   └── test_gold_briefing_workflow.py
└── e2e/
    └── (existing e2e tests)
```

**Structure Decision**: Extend existing `agents/` package with a new `gold/` subpackage. This preserves Bronze/Silver module stability while cleanly separating Gold-tier functionality. Each Gold module extends or wraps existing Silver components (e.g., `safety_gate.py` wraps `hitl_gate.py`, `audit_gold.py` wraps `audit_logger.py`).

---

## Architecture: Component Design

### 1. Persistence Architecture — Ralph Wiggum Loop

**Skill**: `gold-autonomous-loop` | **Contract**: [contracts/autonomous-loop.md](contracts/autonomous-loop.md)

The Ralph Wiggum loop is the execution engine for Gold Tier. It wraps the existing Silver reconciliation-first pattern in a non-terminating outer loop.

**State Machine** (`/Plans/` directory):
```
           ┌──────────────────────────────────────┐
           │          RALPH WIGGUM LOOP            │
           │                                       │
  START ──>│  1. Scan /Plans/ (incomplete plans)   │
           │  2. Scan /Needs_Action/ (tasks)       │
           │  3. Pick next non-blocked item         │
           │  4. Execute step                       │
           │  5. Checkpoint to /Logs/loop-state.json│
           │  6. Log GoldAuditEntry                │
           │                                       │
           │  ┌─ HITL blocked? ──> Skip, try next  │
           │  └─ Step done? ──> Mark [x], continue │
           │                                       │
           │  EXIT PROMISE:                        │
           │  All plans COMPLETE + /Needs_Action/ ∅│
           └──────────────────────────────────────┘
```

**Signal interception**: Register `atexit` + `signal.SIGINT`/`SIGTERM` handlers → call `checkpoint()` before exit. On next startup, `resume()` loads from `/Logs/loop-state.json`.

**Integration with Silver**: The loop calls `reconciler.reconcile()` on startup to find the current mission, then enters the persistent cycle. Plan management uses existing `plan_manager.py` and `plan_parser.py`.

---

### 2. Odoo 19+ Integration Layer

**Skill**: `odoo-accounting` | **Contract**: [contracts/odoo-rpc.md](contracts/odoo-rpc.md)

**JSON-RPC communication strategy**:

```
Agent                    OdooRPCClient              Odoo 19+
  │                          │                         │
  │─── authenticate() ──────>│── POST /jsonrpc ───────>│
  │                          │<── {uid: 2} ───────────│
  │                          │                         │
  │─── search_read() ───────>│── POST /jsonrpc ───────>│
  │<── [invoices...] ────────│<── [{...}, {...}] ──────│
  │                          │                         │
  │─── draft_create() ──────>│                         │
  │                          │── Write to               │
  │                          │   /Pending_Approval/     │
  │                          │   (NO Odoo call yet)     │
  │                          │                         │
  │ [Human approves file]    │                         │
  │                          │                         │
  │─── execute_approved() ──>│── POST /jsonrpc ───────>│
  │<── {result} ─────────────│<── {id: 42} ────────────│
  │                          │── Move to /Done/         │
```

**Data mapping**: See [contracts/odoo-rpc.md](contracts/odoo-rpc.md) for complete Vault → Odoo model mapping. Key models: `account.move` (invoices/journal entries), `account.payment`, `res.partner`.

**Credential isolation**: `OdooConfig` loaded from `.env` only. The `api_key` field is NEVER written to vault files or included in audit log `details` (redacted to `"***"`).

---

### 3. Multi-Channel Social Bridge

**Skill**: `social-media-management` | **Contract**: [contracts/social-bridge.md](contracts/social-bridge.md)

**Architecture**:

```
SocialBridge
├── TwitterAdapter   (max 280 chars, 4 images)
├── FacebookAdapter  (max 63K chars, 10 images)
└── InstagramAdapter (max 2200 chars, 10 carousel)
         │
         ▼
    Browser MCP
    (navigate, click, type, upload)
```

**Session management**: Browser MCP maintains cookies per platform. Each adapter detects session expiry (redirect to login page) and triggers re-authentication. Session cookies stored locally by Browser MCP — not in vault.

**Multi-platform drafting**: `draft_multi_post()` takes a single content string, runs it through each platform adapter's `adapt_content()` method, and creates separate draft files in `/Pending_Approval/` — one per platform. This allows the human to approve/reject per-platform.

**Scheduling**: Draft files include a `Scheduled:` field. The Ralph Wiggum loop checks approved scheduled posts and publishes them when the scheduled time arrives.

---

### 4. CEO Briefing Logic

**Skill**: `ceo-briefing-engine` | **Contract**: [contracts/ceo-briefing.md](contracts/ceo-briefing.md)

**Data aggregation paths**:

```
┌─────────────┐   Revenue MTD    ┌───────────────────┐
│  Odoo 19+   │ ──────────────── │                   │
│  (JSON-RPC) │   account.move   │                   │
└─────────────┘                  │  CEO Briefing     │
                                 │  Engine           │
┌─────────────┐   Stale tasks    │                   │
│ /Needs_Action│ ──────────────── │  ──> /Needs_Action│
│ (vault scan) │   mtime > 48h   │      CEO-Briefing │
└─────────────┘                  │      -YYYY-WNN.md │
                                 │                   │
┌─────────────┐   Subscriptions  │                   │
│ Company_    │ ──────────────── │                   │
│ Handbook.md │   registry data  │                   │
└─────────────┘                  └───────────────────┘
```

**Trigger**: The Ralph Wiggum loop checks `should_generate()` on each iteration. When Sunday 22:00 is reached and no briefing exists for the current ISO week, it triggers `generate_briefing()`.

**Graceful degradation**: Each data source has independent error handling. If Odoo is down (circuit breaker open), the revenue section reads `[DATA UNAVAILABLE — Odoo unreachable]`. The briefing still generates with whatever data IS available.

---

### 5. Error Handling & Resilience

**Skill**: `resilient-operations` | **Contract**: [contracts/resilient-executor.md](contracts/resilient-executor.md)

**Three-layer architecture**:

```
Layer 1: EXPONENTIAL BACKOFF (transient errors)
  HTTP 429, 500-504, timeouts
  Sequence: 1s → 2s → 4s → 8s → 16s (+ jitter, cap 60s)
  Max 5 retries per operation

Layer 2: QUARANTINE-FIRST (logic errors)
  HTTP 400, 401, 403, 422
  ZERO retries — quarantine immediately
  Prefix file with [QUARANTINED]_, create P0 alert

Layer 3: CIRCUIT BREAKER (cascading failure prevention)
  3 consecutive failures to same API → open circuit
  All calls to that API fail-fast for remainder of session
  Log circuit_breaker event
```

**Integration**: Every external call in `odoo_rpc_client.py` and `social_bridge.py` is wrapped in `resilient_executor.execute()`. The executor classifies errors, applies the appropriate layer, and logs all attempts.

---

### 6. Local-First Security

**`.env` structure**: See [research.md](research.md) R6 for the complete `.env` layout.

**Key security rules**:
- `OdooConfig.api_key` is loaded from env and passed in-memory only. Never serialized to vault.
- Audit logs redact credential values: `"api_key": "***"`.
- Browser MCP session cookies are managed by the MCP server, not stored in vault.
- PII detection (inherited from Silver Principle IX) applies to all data entering the vault.

---

## Agent Skill Mapping (Complete)

| # | Feature | Agent Skill | Module | HITL Required | Success Metric |
|---|---|---|---|---|---|
| 1 | Ralph Wiggum Loop | `gold-autonomous-loop` | `agents/gold/autonomous_loop.py` | Pauses on blocked steps | >95% task completion across sessions |
| 2 | Odoo Accounting | `odoo-accounting` | `agents/gold/odoo_rpc_client.py` | All writes + payments >$100 | Transactions recorded <5min |
| 3 | Social Media | `social-media-management` | `agents/gold/social_bridge.py` | ALL posts (no exceptions) | Zero unauthorized posts |
| 4 | CEO Briefing | `ceo-briefing-engine` | `agents/gold/briefing_engine.py` | No (read-only output) | Delivered every Sunday by 23:59 |
| 5 | Resilience | `resilient-operations` | `agents/gold/resilient_executor.py` | Quarantine creates P0 alert | Backoff timing correct, circuit at 3 failures |
| 6 | Audit Trail | `gold-audit-trail` | `agents/gold/audit_gold.py` | No | 100% actions logged with rationale |
| 7 | Safety Gate | `gold-safety-gate` | `agents/gold/safety_gate.py` | IS the HITL mechanism | Zero bypasses of $100 threshold |

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| New `agents/gold/` subpackage (7 modules) | Each Gold feature is a distinct concern requiring isolation | Putting all Gold logic in existing modules would violate single-responsibility and make Silver modules unstable |
| External API dependency (Odoo JSON-RPC) | Constitution XI mandates Odoo integration for financial operations | File-based accounting lacks reconciliation capabilities and partner management |
| Browser MCP dependency for social media | Constitution XII mandates cross-platform social presence | Native APIs require per-platform developer accounts and key management — Browser MCP is simpler for MVP |