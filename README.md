# Personal AI Employee — Hackathon 0

![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)
![License MIT](https://img.shields.io/badge/license-MIT-green)
![Tests](https://img.shields.io/badge/tests-passing-brightgreen)

A production-ready **Obsidian Vault-based AI Employee** system implementing a Bronze–Silver tiered architecture for autonomous task execution with human-in-the-loop safety gates.

> **Docs:** [Architecture](docs/architecture.md) · [Vault Guide](docs/vault-guide.md) · [Contributing](CONTRIBUTING.md) · [Changelog](CHANGELOG.md)

---

## Overview

This project builds an AI Digital FTE (Full-Time Employee) that operates through an Obsidian Vault as its single source of truth. The system implements two tiers:

| Tier | Capability | External Actions |
|------|-----------|-----------------|
| **Bronze** | Inbox triage, task tracking, vault management | None |
| **Silver** | Multi-step reasoning, plan persistence, HITL approval | Via human approval gate |

---

## Silver Tier Features

The Silver Tier adds a full **Reasoning & Planning Loop** on top of Bronze Tier vault management.

### Core Capabilities

#### 1. Autonomous Plan Creation
When a task is detected as "complex" (multi-step, external actions required), the agent:
- Creates a structured `Plan.md` in `/Plans/`
- Breaks the task into ordered, trackable steps
- Marks HITL (Human-In-The-Loop) steps with ✋

```
/Plans/PLAN-2026-001.md
├── YAML frontmatter: task_id, status, priority, created_date
├── # Objective
├── ## Context
├── ## Roadmap (step checkboxes)
└── ## Reasoning Logs (ISO-8601 timestamped)
```

#### 2. Multi-Session Persistence
The agent uses **Reconciliation-First startup** on every session:
1. Scans `/Plans/` for incomplete plans
2. Resumes from the last completed step
3. Prioritizes: Active > Blocked > Draft, newest first

No work is lost between sessions.

#### 3. HITL Safety Gate
**Zero tolerance for unsanctioned external actions.**

Before any email, payment, or external API call:
1. Agent drafts an approval request to `/Pending_Approval/`
2. Agent **halts** — no MCP call is made
3. Human reviews the draft in Obsidian
4. Human moves file to `/Approved/` (or `/Rejected/`)
5. Agent detects the approval and executes via MCP

```
/Pending_Approval/  ← Agent writes here, then stops
/Approved/          ← Human moves file here to authorize
/Rejected/          ← Human moves here to deny
/Done/Actions/      ← Executed actions archived here
```

#### 4. JSON Audit Trail
Every plan operation is appended to `/Logs/YYYY-MM-DD.json` (NDJSON format):
```json
{"timestamp": "2026-02-25T10:01:00Z", "event": "plan_created", "actor": "Agent", "plan_id": "2026-001", "step_id": null, "result": "success", "detail": "Objective: Generate invoice"}
{"timestamp": "2026-02-25T10:01:05Z", "event": "step_completed", "actor": "Agent", "plan_id": "2026-001", "step_id": 1, "result": "success", "detail": "Step 1 completed: Calculate total"}
{"timestamp": "2026-02-25T14:30:03Z", "event": "approval_executed", "actor": "Agent", "plan_id": "2026-001", "step_id": 4, "result": "success", "detail": "action_type=email, file=2026-...md"}
```

#### 5. Block Detection & Alerts
- Plans blocked on approval display alerts in the Dashboard after 24 hours
- Dashboard (`Dashboard.md`) shows real-time plan status, current mission, and blocked plans

#### 6. Error Recovery
- **Corrupted plans**: Automatically quarantined to `/Archive/Corrupted/` — never deleted
- **MCP failures**: Approval file returned to `/Pending_Approval/` with error reason — human can retry
- **Duplicate plans**: `consolidate_duplicate_plans()` merges steps and archives the duplicate

---

## Project Structure

```
├── agents/
│   ├── silver-reasoning-agent.md         # Agent persona, HITL rules, best practices
│   └── skills/
│       └── managing_obsidian_vault/
│           ├── plan_manager.py            # Create, load, update, archive plans
│           ├── approval_manager.py        # HITL approval lifecycle
│           ├── audit_logger.py            # JSON audit trail (T063)
│           ├── complexity_detector.py     # Detect complex tasks
│           ├── dashboard_reconciler.py    # Dashboard sync
│           └── block_manager.py          # Block detection and alerts
├── docs/
│   ├── silver-reasoning-quickstart.md    # Getting started guide
│   └── silver-reasoning-troubleshooting.md  # Recovery procedures
├── specs/
│   └── 003-silver-reasoning/
│       ├── spec.md                       # Requirements
│       ├── plan.md                       # Architecture
│       └── tasks.md                      # 72-task implementation checklist
├── tests/
│   ├── unit/                             # Unit tests
│   ├── integration/                      # Integration tests (per phase)
│   └── e2e/                              # End-to-end integration tests
│       ├── test-invoice-workflow.py      # Full loop: invoice → plan → approval
│       ├── test-multi-session-workflow.py # Multi-session persistence
│       └── test-safety-breach-prevention.py  # HITL safety gate enforcement
├── references/
│   ├── plan-template.md                  # Plan.md schema reference
│   ├── approval-request-template.md      # Approval file schema
│   └── reasoning-log-template.md        # Reasoning log format
└── history/
    ├── prompts/                          # Prompt History Records (PHRs)
    └── adr/                              # Architecture Decision Records
```

---

## Quick Start

See `docs/silver-reasoning-quickstart.md` for complete examples including:
- Invoice workflow (request → plan → approval → completion)
- Multi-session project (interrupted and resumed)
- Safety enforcement demonstration

### Minimal Example

```python
from pathlib import Path
from agents.skills.managing_obsidian_vault.plan_manager import PlanManager
from agents.skills.managing_obsidian_vault.approval_manager import ApprovalManager
from agents.skills.managing_obsidian_vault.audit_logger import AuditLogger

vault = Path("/path/to/vault")
plan_mgr = PlanManager(vault_root=vault)
approval_mgr = ApprovalManager(vault_root=vault)
audit = AuditLogger(vault_root=vault)

# Create a multi-step plan
plan_mgr.create_plan(
    task_id="2026-001",
    objective="Send invoice to Client A",
    context="Client A invoice $1,500",
    steps=["Calculate total", "Generate PDF", "✋ Send email"],
)

# On session resume — automatic
active = plan_mgr.find_active_plan()
```

---

## Running Tests

```bash
# All tests
pytest tests/

# Unit tests only
pytest tests/unit/

# Integration tests
pytest tests/integration/

# E2E tests
pytest tests/e2e/

# Specific E2E scenario
pytest tests/e2e/test-invoice-workflow.py -v
pytest tests/e2e/test-safety-breach-prevention.py -v
```

---

## Documentation

| Document | Description |
|---------|-------------|
| `docs/silver-reasoning-quickstart.md` | Getting started, API cheat-sheet, examples |
| `docs/silver-reasoning-troubleshooting.md` | Recovery procedures for common failures |
| `agents/silver-reasoning-agent.md` | Agent persona, HITL rules, best practices |
| `specs/003-silver-reasoning/spec.md` | Full requirements specification |
| `specs/003-silver-reasoning/plan.md` | Architecture and technical decisions |
| `.specify/memory/constitution.md` | Silver Law compliance rules |

---

## Compliance

This system operates under the **Silver Law** as defined in `.specify/memory/constitution.md`.

Key rules:
- ✅ No external action without a human-approved file in `/Approved/`
- ✅ Reconciliation-First startup on every session
- ✅ All decisions logged with ISO-8601 timestamps
- ✅ Vault is the single source of truth
- ❌ No secrets stored in vault (use `.env`)
- ❌ No autonomous external state changes
