# Research: Gold Tier Autonomous Employee

**Branch**: `004-gold-autonomous-employee` | **Date**: 2026-03-05

## R1: Ralph Wiggum Loop — Persistence Architecture

**Decision**: Extend existing `PlanManager` + `Reconciler` (from Silver) with a non-terminating outer loop that intercepts exit signals and uses `/Plans/` as an auditable state machine.

**Rationale**:
- Silver already implements Reconciliation-First startup (`reconciler.py`) and Plan.md checkpointing (`plan_manager.py`, `plan_parser.py`).
- Gold adds the *persistence guarantee*: the loop MUST NOT exit while items remain in `/Needs_Action/` or incomplete Plans exist in `/Plans/`.
- The `/Plans/` directory already serves as the state machine. Each Plan.md has YAML frontmatter with `status` and a `## Roadmap` with checkboxes. The loop scans these to determine next work.
- File-movement trigger: a task is "done" when its source file moves from `/Needs_Action/` → `/Done/` AND the corresponding Plan roadmap checkbox is marked `[x]`.

**Alternatives considered**:
- SQLite state machine: Rejected — violates Local-First Privacy principle (vault must be the only authorized persistent storage).
- External task queue (Celery, Redis): Rejected — violates 100% local-first constraint.
- Cron-based polling: Rejected — doesn't provide persistence within a session; Ralph Wiggum requires continuous iteration with checkpoint-on-interrupt.

**Key design decisions**:
- Signal interception: Register `atexit` and `signal.SIGINT`/`SIGTERM` handlers to checkpoint current state before exit.
- Iteration counter: Track loop cycle count in log entries (`iteration` field per Constitution XVI).
- Pause semantics: When a step requires HITL approval, skip it and continue to the next non-blocked task. Resume when file appears in `/Approved/`.
- Exit promise: `all(plan.status == COMPLETE for plan in plans) AND len(needs_action_files) == 0`.

---

## R2: Odoo 19+ JSON-RPC Integration Layer

**Decision**: Create an `OdooRPCClient` adapter class that wraps JSON-RPC calls to Odoo's `/jsonrpc` endpoint, mapping vault financial records to Odoo models.

**Rationale**:
- Odoo Community 19+ exposes all models via JSON-RPC at `/jsonrpc` (POST).
- Authentication: `common` service for `authenticate`, `object` service for `execute_kw`.
- Constitution XI mandates: READ operations are autonomous; WRITE operations must be drafted to `/Pending_Approval/`.

**Data mapping** (Vault → Odoo models):
| Vault Entity | Odoo Model | Key Fields |
|---|---|---|
| Invoice | `account.move` (type=out_invoice) | partner_id, invoice_line_ids, amount_total, state |
| Payment | `account.payment` | partner_id, amount, payment_type, journal_id |
| Journal Entry | `account.move` (type=entry) | line_ids (debit/credit), ref, date |
| Partner/Customer | `res.partner` | name, email, vat, property_account_receivable_id |
| Bank Statement | `account.bank.statement` | journal_id, balance_start, balance_end_real |

**JSON-RPC call pattern**:
```
POST /jsonrpc
{
  "jsonrpc": "2.0",
  "method": "call",
  "params": {
    "service": "object",
    "method": "execute_kw",
    "args": [db, uid, password, model, method, args, kwargs]
  }
}
```

**Alternatives considered**:
- Odoo REST API (OCA module): Rejected — requires installing third-party module; JSON-RPC is built-in.
- Direct PostgreSQL access: Rejected — bypasses Odoo's business logic and access controls.
- XML-RPC: Rejected — JSON-RPC is the modern standard for Odoo 17+; XML-RPC is legacy.

---

## R3: Multi-Channel Social Bridge via Browser MCP

**Decision**: Use Browser MCP (`browser-mcp:navigate`, `browser-mcp:click`, `browser-mcp:type`) for all social media interactions. Each platform gets a dedicated adapter module that drafts content to `/Pending_Approval/`.

**Rationale**:
- Constitution XII mandates ALL social posts go through `/Pending_Approval/` — no exceptions.
- Browser MCP provides a unified interface for web-based platforms without requiring individual API keys per platform.
- Platform-specific adapters handle content formatting (character limits, image specs, hashtag strategies).

**Platform constraints**:
| Platform | Max Text | Max Images | Scheduling | Special |
|---|---|---|---|---|
| Twitter/X | 280 chars (free), 25K (Premium) | 4 | Via TweetDeck/scheduled tweets | Thread support |
| Facebook | 63,206 chars | 10 | Native scheduling | Page vs Profile distinction |
| Instagram | 2,200 chars | 10 (carousel) | Via Creator Studio | No link-in-post (use bio) |

**Session management**: Browser MCP maintains session cookies. The adapter must detect expired sessions and re-authenticate. Store platform session state in vault-local JSON (not `.env`).

**Alternatives considered**:
- Native APIs (Twitter API v2, Meta Graph API): Rejected for MVP — requires developer account approval, API key management per platform, and rate limit handling. Browser MCP is sufficient for initial implementation. Can be added as an optimization later.
- Hootsuite/Buffer API: Rejected — third-party dependency violates local-first constraint.

---

## R4: CEO Briefing Engine — Data Aggregation Architecture

**Decision**: Create a `CEOBriefingEngine` class that aggregates data from three sources (Odoo, vault state, Company_Handbook) and generates a structured Markdown briefing in `/Needs_Action/`.

**Rationale**:
- Constitution XIII mandates: Sunday 22:00 trigger, placed in `/Needs_Action/`, must contain Revenue MTD vs Goal, Task Bottlenecks (>48h stale), Subscription Optimizations.
- Data aggregation paths:
  1. **Revenue**: Odoo `account.move` (type=out_invoice, state=posted) filtered by current month → sum `amount_total` → compare with `Company_Handbook.md` monthly target.
  2. **Bottlenecks**: Scan `/Needs_Action/` for files older than 48 hours with no modification → rank by priority.
  3. **Subscriptions**: Read subscription registry from `Company_Handbook.md` → cross-reference with actual usage data (if available from Odoo or manual entries).

**Schedule mechanism**: CronWatcher checks system time. When `weekday == 6` (Sunday) and `hour >= 22` and no briefing exists for current week → trigger generation.

**Alternatives considered**:
- APScheduler (Python library): Viable but adds dependency. CronWatcher is already planned as a watcher type.
- OS-level cron: Rejected — not portable across platforms; violates "all AI as Agent Skills" requirement.

---

## R5: Error Handling & Resilience Patterns

**Decision**: Implement three-layer resilience: (1) Exponential backoff for transient errors, (2) Quarantine-first for logic errors, (3) Circuit breaker for repeated failures.

**Rationale**:
- Constitution XIV defines exact behavior:
  - Transient (429, 5xx, timeout): backoff 1s → 2s → 4s → 8s → 16s → max 60s, up to 5 retries.
  - Logic (400, 401, 403, 422): NO retry, quarantine with `[QUARANTINED]` prefix, P0 alert.
  - Circuit breaker: 3 consecutive failures → disable integration for current session.

**Implementation approach**:
- `ResilientExecutor` class wrapping all external calls.
- Decorator pattern: `@resilient(max_retries=5, backoff_factor=1.0)` for any MCP/API call.
- Error classification function: HTTP status → `TransientError` or `LogicError`.
- Quarantine writes to `/Needs_Action/[QUARANTINED]_<original-filename>.md` with full error context.

**Alternatives considered**:
- `tenacity` library: Good fit for retry logic but adds external dependency. Custom implementation preferred to keep dependency count low and control exact Constitution-mandated behavior.
- Global try/catch: Rejected — doesn't distinguish transient vs logic errors.

---

## R6: Local-First Security & .env Structure

**Decision**: All secrets in a single `.env` file at repo root. Vault files MUST NEVER contain credentials. PII detection inherited from Silver (Principle IX).

**Rationale**:
- Constitution I (Local-First Privacy) and XI (Odoo credentials) mandate `.env`-only secret storage.
- The existing `.env.example` covers sentinel config. Gold Tier extends it with Odoo and social media credentials.

**Required `.env` structure for Gold Tier**:

```env
# === Sentinel (existing) ===
WATCH_DIRECTORY=/path/to/watch
VAULT_INBOX_PATH=/path/to/vault/Inbox
STABILITY_SECONDS=2.0
ALLOWED_EXTENSIONS=.md,.txt,.pdf,.jpg,.jpeg,.png
LOG_LEVEL=INFO

# === Odoo 19+ JSON-RPC ===
ODOO_URL=http://localhost:8069
ODOO_DB=my_company
ODOO_USERNAME=admin
ODOO_API_KEY=your-odoo-api-key-here

# === CEO Briefing ===
CEO_BRIEFING_DAY=6          # 0=Mon, 6=Sun
CEO_BRIEFING_HOUR=22        # 24h format
REVENUE_MONTHLY_GOAL=10000  # Fallback if not in Company_Handbook

# === HITL Thresholds ===
PAYMENT_APPROVAL_THRESHOLD=100.00

# === Browser MCP ===
BROWSER_MCP_HOST=localhost
BROWSER_MCP_PORT=3000
```

**No social media API keys in .env** for MVP — Browser MCP handles authentication via browser sessions. If native APIs are added later, keys would go here.

**Alternatives considered**:
- HashiCorp Vault: Overkill for single-user local-first system.
- Encrypted .env: Nice-to-have but not required at this tier. Can be added as a hardening step.

---

## R7: Agent Skill Mapping

**Decision**: Every Gold Tier feature maps to a discrete Agent Skill that can be independently tested and upgraded.

| Feature | Agent Skill | Key Module(s) |
|---|---|---|
| Ralph Wiggum Loop | `gold-autonomous-loop` | `autonomous_loop.py`, extends `plan_manager.py` |
| Odoo Accounting | `odoo-accounting` | `odoo_rpc_client.py`, `financial_handler.py` |
| Social Media | `social-media-management` | `social_bridge.py`, platform adapters |
| CEO Briefing | `ceo-briefing-engine` | `briefing_engine.py`, `subscription_auditor.py` |
| Resilience | `resilient-operations` | `resilient_executor.py`, error classifiers |
| Audit Logging | `gold-audit-trail` | Extends existing `audit_logger.py` with Gold schema |
| HITL Gating | `gold-safety-gate` | Extends existing `hitl_gate.py` with $100 threshold |

All skills inherit from a base pattern and are registered in the `managing-obsidian-vault` skill or a new Gold-tier umbrella skill.