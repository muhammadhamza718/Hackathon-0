# Data Model: Gold Tier Autonomous Employee

**Branch**: `004-gold-autonomous-employee` | **Date**: 2026-03-05

## Existing Entities (inherited from Bronze/Silver)

These are already implemented in `agents/` and remain unchanged:

| Entity | Module | Description |
|---|---|---|
| `PlanStatus` | `plan_manager.py` | Enum: DRAFT, ACTIVE, COMPLETE, CANCELLED |
| `PlanSummary` | `plan_parser.py` | Frozen dataclass: parsed Plan.md with progress |
| `PlanStep` | `plan_parser.py` | TypedDict: step text, checked status |
| `ComplexityLevel` | `complexity_detector.py` | IntEnum: SIMPLE=0, COMPLEX=1 |
| `Priority` | `inbox_scanner.py` | IntEnum: CRITICAL=0, HIGH=1, MEDIUM=2, LOW=3 |
| `Decision` | `hitl_gate.py` | Enum: APPROVED, REJECTED, PENDING |
| `AuditEntry` | `audit_logger.py` | Frozen dataclass: timestamp, tier, action, detail |
| `ReconcileResult` | `reconciler.py` | Frozen dataclass: next plan to resume |
| `VaultStatus` | `dashboard_writer.py` | Frozen dataclass: folder counts |

---

## New Entities (Gold Tier)

### 1. GoldAuditEntry (extends AuditEntry)

Extends the existing audit entry with Gold-tier mandatory fields per Constitution XVI.

```
Fields:
  timestamp: str (ISO-8601)
  action: str (valid Gold actions: odoo_read, odoo_write_draft, social_draft,
               social_post, ceo_briefing, subscription_audit, circuit_breaker,
               retry, quarantine — plus all Silver/Bronze actions)
  source_file: str (vault-relative path)
  details: str (human-readable description)
  result: str (success | failure | warning | skipped)
  rationale: str (MANDATORY — Plan step reference e.g. "Plan-2026-001#Step-3"
                  or explanation if no Plan exists)
  iteration: int (Ralph Wiggum loop cycle count)
  tier: str (always "gold")
  duration_ms: int (execution time in milliseconds)
```

**Validation rules**:
- `rationale` MUST NOT be empty or null.
- `iteration` MUST be >= 0.
- `action` MUST be from the valid action set.

---

### 2. LoopState

Captures the Ralph Wiggum loop's current position for checkpoint/resume.

```
Fields:
  session_id: str (unique per agent session)
  iteration: int (current loop cycle count)
  active_plan_id: str | None (currently executing plan ID)
  active_step_index: int | None (current step within active plan)
  blocked_plans: list[str] (plan IDs waiting on HITL approval)
  last_checkpoint: str (ISO-8601 timestamp of last save)
  exit_promise_met: bool (True when all plans complete and /Needs_Action/ empty)
```

**Storage**: `/Logs/loop-state.json` (overwritten each iteration).

**State transitions**:
- On startup: Load from `loop-state.json` if exists (resume), else initialize fresh.
- On each iteration: Update `iteration`, `active_plan_id`, `active_step_index`, `last_checkpoint`.
- On HITL block: Add plan to `blocked_plans`, advance to next non-blocked plan.
- On completion: Set `exit_promise_met = True`.

---

### 3. OdooSession

Holds authenticated session state for Odoo JSON-RPC calls.

```
Fields:
  url: str (from ODOO_URL env var)
  database: str (from ODOO_DB env var)
  uid: int (authenticated user ID, obtained from /jsonrpc authenticate call)
  api_key: str (from ODOO_API_KEY env var — never persisted to vault)
  authenticated: bool
  last_call: str | None (ISO-8601 timestamp of last successful API call)
```

**Validation rules**:
- `uid` MUST be > 0 after successful authentication.
- `api_key` MUST NOT appear in any vault file or log entry.

---

### 4. OdooOperation

Represents a pending or completed Odoo API call.

```
Fields:
  operation_id: str (unique)
  model: str (Odoo model name, e.g. "account.move")
  method: str (Odoo method, e.g. "create", "search_read", "write")
  args: list (positional arguments for execute_kw)
  kwargs: dict (keyword arguments for execute_kw)
  is_write: bool (True for create/write/unlink operations)
  requires_approval: bool (True if write operation or amount > $100)
  status: str (pending | approved | executed | failed | quarantined)
  result: any | None (API response data)
  error: str | None (error message if failed)
  json_rpc_payload: dict (full JSON-RPC request body — logged for audit)
```

---

### 5. SocialDraft

Represents a social media post draft per Constitution XII format.

```
Fields:
  draft_id: str (unique)
  platform: str (X | Facebook | Instagram | Multi)
  content: str (post text, respecting platform character limits)
  media_paths: list[str] (vault-relative paths to attached images/videos)
  scheduled: str (ISO-8601 timestamp or "immediate")
  rationale: str (Plan step reference or business goal)
  approval_status: str (pending | approved | rejected)
  approval_file_path: str (path in /Pending_Approval/)
  adapted_versions: dict[str, str] (platform → adapted content, for Multi posts)
```

**Validation rules**:
- Twitter/X content: max 280 chars (free tier).
- Facebook content: max 63,206 chars.
- Instagram content: max 2,200 chars.
- `media_paths` must reference existing files.
- `rationale` MUST NOT be empty.

---

### 6. CEOBriefing

Represents a generated weekly briefing per Constitution XIII.

```
Fields:
  briefing_id: str (format: "BRIEFING-YYYY-WNN" where NN is ISO week number)
  generated_at: str (ISO-8601)
  period_start: str (ISO-8601 — Monday of the reporting week)
  period_end: str (ISO-8601 — Sunday of the reporting week)
  revenue_mtd: float | None (month-to-date revenue from Odoo)
  revenue_goal: float (monthly target from Company_Handbook or env)
  revenue_delta_pct: float | None (percentage above/below goal)
  bottleneck_tasks: list[BottleneckTask] (tasks in /Needs_Action/ > 48h)
  subscription_findings: list[SubscriptionFinding] (optimization recommendations)
  data_unavailable: list[str] (sections where source data was missing)
  output_path: str (vault-relative path in /Needs_Action/)
```

### 6a. BottleneckTask (nested)

```
Fields:
  filename: str
  age_hours: float (hours since last modification)
  priority: str (from file content or metadata)
  summary: str (first line or title)
```

### 6b. SubscriptionFinding (nested)

```
Fields:
  service_name: str
  monthly_cost: float
  utilization_pct: float | None
  market_rate: float | None
  finding_type: str (underused | overpriced | unused)
  recommendation: str
  potential_savings: float
```

---

### 7. CircuitBreakerState

Tracks consecutive failures per API endpoint for circuit breaker pattern.

```
Fields:
  api_name: str (e.g. "odoo", "browser_mcp", "twitter")
  consecutive_failures: int
  is_open: bool (True = circuit is open, calls are blocked)
  last_failure: str | None (ISO-8601)
  last_error: str | None (most recent error message)
  opened_at: str | None (ISO-8601 when circuit was opened)
```

**State transitions**:
- Each failure: increment `consecutive_failures`.
- At 3 consecutive failures: set `is_open = True`, log circuit_breaker event.
- On success: reset `consecutive_failures = 0`, set `is_open = False`.
- Circuit open: all calls to this API return immediately with a circuit-open error.

---

### 8. QuarantinedItem

Represents a failed operation that has been quarantined per Constitution XIV.

```
Fields:
  original_filename: str
  quarantined_filename: str (prefixed with "[QUARANTINED]_")
  error_type: str (logic_error | system_error)
  http_status: int | None
  error_message: str
  original_payload: dict (the failed request data)
  quarantined_at: str (ISO-8601)
  alert_created: bool (True if P0 alert was generated)
  resolution: str | None (how it was resolved, if at all)
```

---

## Entity Relationships

```
LoopState ──references──> PlanSummary (via active_plan_id)
LoopState ──references──> blocked PlanSummary[] (via blocked_plans)
PlanSummary ──contains──> PlanStep[]
OdooOperation ──may-create──> ApprovalRequest (via /Pending_Approval/)
SocialDraft ──always-creates──> ApprovalRequest (via /Pending_Approval/)
CEOBriefing ──reads──> OdooSession (for revenue data)
CEOBriefing ──reads──> vault /Needs_Action/ (for bottlenecks)
CEOBriefing ──reads──> Company_Handbook.md (for subscription registry)
CircuitBreakerState ──gates──> OdooOperation, SocialDraft
QuarantinedItem ──created-from──> OdooOperation (on logic failure)
GoldAuditEntry ──logs──> all operations above
```