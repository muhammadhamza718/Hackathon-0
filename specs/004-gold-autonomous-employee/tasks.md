# Tasks: Gold Tier Autonomous Employee

**Input**: Design documents from `/specs/004-gold-autonomous-employee/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Included — each user story has explicit test tasks.

**Organization**: Tasks grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create `agents/gold/` package, extend constants/exceptions, define all data models.

- [ ] T001 Create `agents/gold/__init__.py` with public API exports
- [ ] T002 [P] Create Gold-tier data models in `agents/gold/models.py` (GoldAuditEntry, LoopState, OdooSession, OdooOperation, SocialDraft, CEOBriefing, CircuitBreakerState, QuarantinedItem)
- [ ] T003 [P] Add Gold-specific exceptions to `agents/exceptions.py` (OdooError, SocialMediaError, BriefingError, CircuitOpenError, QuarantineError)
- [ ] T004 [P] Add Gold action types and constants to `agents/constants.py` (GOLD_ACTIONS, LOOP_STATE_FILE, BRIEFING_PREFIX, QUARANTINE_PREFIX, PAYMENT_THRESHOLD)
- [ ] T005 [P] Update `.env.example` with Gold Tier environment variables (ODOO_URL, ODOO_DB, ODOO_USERNAME, ODOO_API_KEY, BROWSER_MCP_HOST, BROWSER_MCP_PORT, CEO_BRIEFING_DAY, CEO_BRIEFING_HOUR, PAYMENT_APPROVAL_THRESHOLD)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core modules that ALL user stories depend on.

- [ ] T006 Implement Gold-tier audit logger in `agents/gold/audit_gold.py` (extends existing `audit_logger.py` with rationale, iteration, duration_ms, tier="gold", JSON format in YYYY-MM-DD.json)
- [ ] T007 Implement Gold-tier safety gate in `agents/gold/safety_gate.py` (wraps `hitl_gate.py`, adds $100 payment threshold check, social post detection, Odoo write gating)
- [ ] T008 Implement resilient executor in `agents/gold/resilient_executor.py` (exponential backoff 1s→2s→4s→8s→16s with jitter, max 5 retries, error classification, quarantine for logic errors, circuit breaker at 3 consecutive failures)

### Tests for Foundational

- [ ] T009 [P] Write unit tests in `tests/unit/test_gold_audit.py` (GoldAuditEntry creation, rationale validation, JSON log format, action type validation)
- [ ] T010 [P] Write unit tests in `tests/unit/test_gold_safety_gate.py` ($100 threshold, social post detection, Odoo write gating, below-threshold pass-through)
- [ ] T011 [P] Write unit tests in `tests/unit/test_gold_resilient_executor.py` (backoff timing, error classification, quarantine on logic error, circuit breaker open at 3 failures, jitter range, success resets breaker)

**Checkpoint**: Foundation ready — user story implementation can begin.

---

## Phase 3: User Story 1 — Ralph Wiggum Autonomous Loop (Priority: P1) MVP

**Goal**: Persistent reasoning loop that iterates across sessions until exit promise met.

**Independent Test**: Create a 3-step plan, execute 1 step, simulate restart, verify resume from step 2.

### Tests for US1

- [ ] T012 [P] [US1] Write unit tests in `tests/unit/test_gold_autonomous_loop.py` (checkpoint save/load, exit promise evaluation, HITL skip logic, signal handler registration, iteration counter increment, max_iterations safety cap)
- [ ] T013 [P] [US1] Write integration test in `tests/integration/test_gold_loop_lifecycle.py` (3-step plan → execute 1 → checkpoint → resume → complete remaining → exit promise met)

### Implementation for US1

- [ ] T014 [US1] Implement `AutonomousLoop` class in `agents/gold/autonomous_loop.py` — constructor accepting vault_root and LoopConfig, signal handler registration (atexit + SIGINT/SIGTERM), checkpoint() writing LoopState to `/Logs/loop-state.json`
- [ ] T015 [US1] Implement `resume()` method in `agents/gold/autonomous_loop.py` — load LoopState from `/Logs/loop-state.json`, return None if fresh start
- [ ] T016 [US1] Implement `run()` main loop in `agents/gold/autonomous_loop.py` — scan /Plans/ for incomplete plans, scan /Needs_Action/ for tasks, pick next non-blocked item, execute step, checkpoint, log GoldAuditEntry per iteration
- [ ] T017 [US1] Implement `is_exit_promise_met()` in `agents/gold/autonomous_loop.py` — returns True when all plans COMPLETE/CANCELLED AND /Needs_Action/ empty
- [ ] T018 [US1] Implement HITL skip logic — when step requires approval, add plan to blocked_plans, advance to next non-blocked task, continue loop

**Checkpoint**: Ralph Wiggum loop functional — can persist/resume across sessions.

---

## Phase 4: User Story 2 — Odoo 19+ Accounting Integration (Priority: P2)

**Goal**: JSON-RPC client for Odoo with READ autonomous, WRITE via /Pending_Approval/.

**Independent Test**: Authenticate to Odoo mock, search_read invoices, draft_create an invoice to /Pending_Approval/.

### Tests for US2

- [ ] T019 [P] [US2] Write unit tests in `tests/unit/test_gold_odoo_rpc.py` (authenticate success/failure, search_read returns records, draft_create writes to /Pending_Approval/, execute_approved requires /Approved/ file, credential redaction in logs, JSON-RPC payload construction)
- [ ] T020 [P] [US2] Write integration test in `tests/integration/test_gold_odoo_integration.py` (full lifecycle: authenticate → search_read → draft_create → approve → execute_approved → verify /Done/)

### Implementation for US2

- [ ] T021 [US2] Implement `OdooConfig` loader in `agents/gold/odoo_rpc_client.py` — load from .env via python-dotenv, validate required fields (url, database, username, api_key)
- [ ] T022 [US2] Implement `OdooRPCClient.authenticate()` in `agents/gold/odoo_rpc_client.py` — POST to /jsonrpc with common service, return OdooSession with uid
- [ ] T023 [US2] Implement `OdooRPCClient.search_read()` and `read()` in `agents/gold/odoo_rpc_client.py` — autonomous READ operations wrapped in resilient_executor
- [ ] T024 [US2] Implement `OdooRPCClient.draft_create()` and `draft_write()` in `agents/gold/odoo_rpc_client.py` — write OdooOperation as approval file to /Pending_Approval/ with full JSON-RPC payload
- [ ] T025 [US2] Implement `OdooRPCClient.execute_approved()` in `agents/gold/odoo_rpc_client.py` — verify file in /Approved/, execute against Odoo, move to /Done/, log audit entry

**Checkpoint**: Odoo integration functional — can read data autonomously, write operations go through approval.

---

## Phase 5: User Story 3 — Multi-Platform Social Media (Priority: P3)

**Goal**: Draft social posts for X/Facebook/Instagram via Browser MCP, all through /Pending_Approval/.

**Independent Test**: Draft a multi-platform post, verify 3 files in /Pending_Approval/ with correct content adaptation.

### Tests for US3

- [ ] T026 [P] [US3] Write unit tests in `tests/unit/test_gold_social_bridge.py` (content adaptation per platform limits, draft_post creates approval file, draft_multi_post creates per-platform files, media path validation, engagement summary structure)
- [ ] T027 [P] [US3] Write integration test — draft_multi_post → verify /Pending_Approval/ files → simulate approval → verify publish_approved moves to /Done/

### Implementation for US3

- [ ] T028 [US3] Implement platform adapters in `agents/gold/social_bridge.py` — TwitterAdapter (280 chars, 4 images), FacebookAdapter (63K chars, 10 images), InstagramAdapter (2200 chars, 10 carousel) each with `adapt_content()` method
- [ ] T029 [US3] Implement `SocialBridge.draft_post()` in `agents/gold/social_bridge.py` — validate content, create SocialDraft, write approval file to /Pending_Approval/ with Constitution XII format (Platform, Content, Media, Scheduled, Rationale)
- [ ] T030 [US3] Implement `SocialBridge.draft_multi_post()` in `agents/gold/social_bridge.py` — adapt content per platform, create separate draft per platform
- [ ] T031 [US3] Implement `SocialBridge.publish_approved()` in `agents/gold/social_bridge.py` — verify /Approved/ file, construct Browser MCP actions, execute via resilient_executor, move to /Done/
- [ ] T032 [US3] Implement `SocialBridge.get_engagement_summary()` in `agents/gold/social_bridge.py` — Browser MCP READ for analytics, return EngagementSummary

**Checkpoint**: Social media management functional — draft/approve/publish workflow works for all 3 platforms.

---

## Phase 6: User Story 4 — CEO Briefing Engine (Priority: P4)

**Goal**: Weekly auto-generated briefing with revenue, bottlenecks, subscription audit.

**Independent Test**: Trigger briefing with mock data, verify Markdown output in /Needs_Action/.

### Tests for US4

- [ ] T033 [P] [US4] Write unit tests in `tests/unit/test_gold_briefing_engine.py` (should_generate trigger logic, revenue aggregation, bottleneck detection >48h, subscription finding types, graceful degradation on missing data, briefing ID format)
- [ ] T034 [P] [US4] Write integration test in `tests/integration/test_gold_briefing_workflow.py` (full briefing generation with mock Odoo + vault files → verify output in /Needs_Action/CEO-Briefing-YYYY-WNN.md)

### Implementation for US4

- [ ] T035 [US4] Implement `CEOBriefingEngine.should_generate()` in `agents/gold/briefing_engine.py` — check weekday/hour matches config, no existing briefing for current ISO week
- [ ] T036 [US4] Implement revenue aggregation in `agents/gold/briefing_engine.py` — use OdooRPCClient.search_read() for account.move MTD, compare with goal from Company_Handbook or env fallback
- [ ] T037 [US4] Implement bottleneck detection in `agents/gold/briefing_engine.py` — scan /Needs_Action/ for files with mtime >48h, extract priority and summary
- [ ] T038 [US4] Implement subscription auditor in `agents/gold/briefing_engine.py` — parse Company_Handbook.md for subscription registry, flag underused (<30%) and overpriced (>20% above market)
- [ ] T039 [US4] Implement `write_briefing()` in `agents/gold/briefing_engine.py` — render Markdown with Revenue table, Bottleneck table, Subscription table, write to /Needs_Action/CEO-Briefing-YYYY-WNN.md

**Checkpoint**: CEO briefing engine functional — generates accurate weekly reports on schedule.

---

## Phase 7: User Story 5 — Resilient Operations (Priority: P5)

**Note**: Core resilience (T008) already in Phase 2. This phase adds integration with Odoo and Social Bridge.

- [ ] T040 [US5] Wire resilient_executor into OdooRPCClient — all search_read/read/execute calls wrapped in `resilient_executor.execute()`
- [ ] T041 [US5] Wire resilient_executor into SocialBridge — all publish_approved/get_engagement calls wrapped
- [ ] T042 [US5] Implement quarantine file creation in `agents/gold/resilient_executor.py` — on logic error, rename with [QUARANTINED]_ prefix, create P0 alert in /Needs_Action/

---

## Phase 8: User Story 6 — Audit and Safety Controls (Priority: P6)

**Note**: Core audit (T006) and safety gate (T007) already in Phase 2. This phase adds cross-cutting integration.

- [ ] T043 [US6] Wire GoldAuditLogger into AutonomousLoop — every iteration logged with action, rationale, iteration count, duration_ms
- [ ] T044 [US6] Wire GoldAuditLogger into OdooRPCClient — every RPC call logged with redacted payload
- [ ] T045 [US6] Wire GoldAuditLogger into SocialBridge — every draft/publish logged with platform and rationale
- [ ] T046 [US6] Wire GoldAuditLogger into CEOBriefingEngine — briefing generation logged with data source status
- [ ] T047 [US6] Wire GoldSafetyGate into AutonomousLoop — check every action before execution, route to /Pending_Approval/ if needed

---

## Phase 9: Polish & Cross-Cutting Concerns

- [ ] T048 [P] Update `agents/__init__.py` with Gold tier exports
- [ ] T049 [P] Update `.env.example` at repo root with complete Gold Tier variables
- [ ] T050 Run all tests and verify >70% coverage for `agents/gold/` package

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies
- **Phase 2 (Foundational)**: Depends on Phase 1
- **Phase 3-6 (User Stories)**: All depend on Phase 2. Can run in parallel.
- **Phase 7-8 (Integration)**: Depends on Phases 3-6
- **Phase 9 (Polish)**: Depends on all prior phases

### Within Each User Story

- Tests written first (TDD)
- Models before services
- Core implementation before integration
- Story complete before wiring cross-cutting concerns

### Parallel Opportunities

- T002, T003, T004, T005 can run in parallel (Phase 1)
- T009, T010, T011 can run in parallel (Phase 2 tests)
- Once Phase 2 completes, Phases 3-6 can run in parallel
- All [P] marked tasks within a phase can run in parallel

## Implementation Strategy

### MVP First (US1 Only)
1. Complete Phase 1 + Phase 2
2. Complete Phase 3 (Ralph Wiggum Loop)
3. STOP and VALIDATE

### Incremental Delivery
1. Phase 1+2 → Foundation
2. Phase 3 → Persistent autonomy (MVP)
3. Phase 4 → Odoo accounting
4. Phase 5 → Social media
5. Phase 6 → CEO briefing
6. Phase 7+8 → Cross-cutting wiring
7. Phase 9 → Polish
