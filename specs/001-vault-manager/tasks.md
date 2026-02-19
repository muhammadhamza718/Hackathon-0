# Tasks: Vault Manager — Bronze Tier

**Input**: Design documents from `/specs/001-vault-manager/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/operations.md

**Organization**: Tasks grouped by user story for independent implementation. Each story is a complete, testable increment.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story (US1–US5 from spec.md)

---

## Phase 1: Setup

**Purpose**: Skill structure verification and Bronze Tier alignment

- [ ] T001 Verify managing-obsidian-vault skill structure exists at `.agents/skills/managing-obsidian-vault/SKILL.md` with all reference files (vault-structure.md, triage-rules.md, dashboard-template.md, handbook-template.md, log-format.md)
- [ ] T002 [P] Update SKILL.md Section 1 to scope vault initialization to Bronze Tier folders only (/Inbox, /Needs_Action, /Done, /Logs, /Pending_Approval) — remove /Plans and /Approved references per Bronze Law review findings at `.agents/skills/managing-obsidian-vault/SKILL.md`
- [ ] T003 [P] Update `references/vault-structure.md` to mark folders by tier (Bronze required: Inbox, Needs_Action, Done, Logs, Pending_Approval; Silver+: Plans, Approved) at `.agents/skills/managing-obsidian-vault/references/vault-structure.md`
- [ ] T004 [P] Validate Bronze Law compliance: grep SKILL.md and all reference files for any references to external APIs, network calls, MCP servers, or Ralph Wiggum loops — confirm zero matches at `.agents/skills/managing-obsidian-vault/`

**Checkpoint**: Skill structure verified, Bronze Tier alignment confirmed

---

## Phase 2: Foundational — Audit Logger (M5)

**Purpose**: Cross-cutting dependency — every other module needs logging before it can be built

**No user story work can begin until this phase is complete.**

- [ ] T005 Verify `references/log-format.md` contains complete JSON schema with all valid actions (triage, complete, move, create, update_dashboard, error) and results (success, failure, warning, skipped) at `.agents/skills/managing-obsidian-vault/references/log-format.md`
- [ ] T006 Verify SKILL.md Section 5 (Audit Logging) includes: read-parse-append-write pattern, create-if-missing logic (`[]` initialization), malformed JSON recovery (.bak + fresh start), and "never skip logging even on errors" rule at `.agents/skills/managing-obsidian-vault/SKILL.md`
- [ ] T007 Add explicit log entry examples to `references/log-format.md` for each action type: triage (with rationale in details), complete, move, create, update_dashboard, error — ensure each example shows the decision rationale field at `.agents/skills/managing-obsidian-vault/references/log-format.md`

**Verification**: Read `references/log-format.md` and confirm: (1) JSON schema has all 5 required fields, (2) all 6 action types documented, (3) all 4 result types documented, (4) examples show decision rationale in details field, (5) malformed JSON recovery procedure documented.

**Checkpoint**: Audit logging fully specified — all modules can now reference it

---

## Phase 3: User Story 1 — Initialize a New Vault (Priority: P1) MVP

**Goal**: User points Claude at an empty directory, asks to "set up my vault," and gets a complete, healthy vault with all folders and core files.

**Independent Test**: Run vault init on an empty temp directory. Verify: 5 folders exist, Dashboard.md has 4 sections with empty-state messages, Company_Handbook.md has Bronze Tier rules, health check passes, audit log entry written.

### Implementation for User Story 1

- [ ] T008 [US1] Update SKILL.md Section 1 step 1 to list exact Bronze Tier folders to create: `/Inbox`, `/Needs_Action`, `/Done`, `/Logs`, `/Pending_Approval` — using `Bash(mkdir -p)` for idempotent creation at `.agents/skills/managing-obsidian-vault/SKILL.md`
- [ ] T009 [US1] Update `references/dashboard-template.md` to include empty-state messages for all 4 sections (Pending Actions: "No pending actions.", Recently Completed: "No completed items yet.", Stats: all zeros, Alerts: "No active alerts.") and ISO-8601 timestamp placeholder at `.agents/skills/managing-obsidian-vault/references/dashboard-template.md`
- [ ] T010 [US1] Update `references/handbook-template.md` to ensure Bronze Tier focus: CAN/CANNOT lists accurate, Upgrade Path section marked as aspirational, VIP/Blocked placeholders present, all autonomy boundaries match constitution at `.agents/skills/managing-obsidian-vault/references/handbook-template.md`
- [ ] T011 [US1] Add health check procedure to SKILL.md Section 1 step 4: verify 5 folders exist + 2 core files present and non-empty, report item count ("7 items verified"), list any missing items at `.agents/skills/managing-obsidian-vault/SKILL.md`
- [ ] T012 [US1] Add idempotency rule to SKILL.md Section 1: "If file already exists, do NOT overwrite. Only create missing items. Report 'vault healthy' if all items present." at `.agents/skills/managing-obsidian-vault/SKILL.md`

**Verification**:
1. Create empty temp directory
2. Ask Claude: "Set up my AI employee vault at [temp-dir]"
3. Run `ls -R [temp-dir]` — verify 5 folders: Inbox, Needs_Action, Done, Logs, Pending_Approval
4. Read Dashboard.md — verify 4 sections with empty-state messages, ISO-8601 timestamp
5. Read Company_Handbook.md — verify Bronze Tier rules, CAN/CANNOT lists
6. Read Logs/YYYY-MM-DD.json — verify initialization log entry with action: "create"
7. Re-run init — verify "vault healthy" with no files modified

**Checkpoint**: User Story 1 complete — empty directory → fully functional vault

---

## Phase 4: User Story 2 — Triage Inbox Items (Priority: P1) MVP

**Goal**: User drops files in /Inbox/, asks "process my inbox," and each file is classified by priority, routed correctly, and logged.

**Independent Test**: Place 3 files in /Inbox/ (urgent email, meeting request, newsletter). Run triage. Verify: urgent → /Needs_Action/ as #high, meeting → /Needs_Action/ as #medium, newsletter → /Done/. Dashboard updated. Log has 3 triage entries + 1 dashboard update.

### Implementation for User Story 2

- [ ] T013 [US2] Verify SKILL.md Section 2 step 2 includes: read Company_Handbook.md FIRST, extract priority keywords, fall back to triage-rules.md defaults if handbook missing or empty at `.agents/skills/managing-obsidian-vault/SKILL.md`
- [ ] T014 [US2] Update `references/triage-rules.md` to add explicit classification logic flowchart: (1) check HIGH keywords → #high, (2) check MEDIUM keywords → #medium, (3) default → #low, (4) Company_Handbook.md overrides at `.agents/skills/managing-obsidian-vault/references/triage-rules.md`
- [ ] T015 [US2] Verify SKILL.md Section 2 frontmatter parsing handles all cases: valid YAML → extract fields, no frontmatter → file_drop + warning, malformed → error + skip at `.agents/skills/managing-obsidian-vault/SKILL.md`
- [ ] T016 [US2] Verify SKILL.md Section 2 routing logic: actionable items → create file in /Needs_Action/ with format `- [ ] [[Inbox/FILE]] | Summary | #priority | @date`, informational → move to /Done/ at `.agents/skills/managing-obsidian-vault/SKILL.md`
- [ ] T017 [US2] Add empty inbox handling to SKILL.md Section 2: "If /Inbox/ is empty, log 'no items to triage' with action: triage, result: skipped, update Dashboard stats, done." at `.agents/skills/managing-obsidian-vault/SKILL.md`
- [ ] T018 [US2] Update `references/triage-rules.md` actionable-vs-informational criteria to include explicit examples: newsletters → informational, FYI → informational, requests/questions/deadlines/financials → actionable at `.agents/skills/managing-obsidian-vault/references/triage-rules.md`

**Verification**:
1. Initialize vault (US1 prerequisite)
2. Create 3 test files in /Inbox/:
   - `urgent-email.md` with frontmatter `type: email`, body containing "URGENT invoice payment"
   - `meeting-request.md` with frontmatter `type: email`, body containing "schedule meeting"
   - `newsletter.md` with frontmatter `type: email`, body containing "Weekly roundup. No action required."
3. Ask Claude: "Process my inbox"
4. Verify /Needs_Action/ has 2 files (urgent=#high, meeting=#medium)
5. Verify /Done/ has newsletter
6. Verify /Inbox/ is empty (files moved)
7. Read Logs/YYYY-MM-DD.json — verify 3 triage entries with rationale + 1 update_dashboard
8. Read Dashboard.md — verify 2 pending items, 1 done

**Checkpoint**: User Story 2 complete — inbox triage pipeline working

---

## Phase 5: User Story 3 — View Live Dashboard (Priority: P2)

**Goal**: Dashboard.md always reflects actual vault state with correct counts, sorted pending items, recent completions, and alerts for overdue #high items.

**Independent Test**: Populate vault with known items. Trigger dashboard rebuild. Verify all 4 sections match actual folder contents.

### Implementation for User Story 3

- [ ] T019 [US3] Verify SKILL.md Section 3 includes full read-then-write rebuild pattern: (1) Glob each folder for counts, (2) Read /Needs_Action/ for pending items sorted #high first, (3) Read /Done/ last 10 by date, (4) Compute alerts (#high > 24h), (5) Write from template at `.agents/skills/managing-obsidian-vault/SKILL.md`
- [ ] T020 [US3] Update `references/dashboard-template.md` to include: (1) table-based Pending Actions with columns Status/Item/Summary/Priority/Date, (2) table-based Recently Completed, (3) Stats table for all Bronze Tier folders, (4) Alerts table with age column, (5) auto-generated footer note at `.agents/skills/managing-obsidian-vault/references/dashboard-template.md`
- [ ] T021 [US3] Add "never use cached values" rule explicitly to SKILL.md Section 3: "ALWAYS count actual files via Glob. NEVER reuse counts from a previous operation. Dashboard MUST reflect reality." at `.agents/skills/managing-obsidian-vault/SKILL.md`
- [ ] T022 [US3] Add alert computation logic to SKILL.md Section 3: "For each #high item in /Needs_Action/, check @date. If date is > 24 hours old, add to Alerts section with age in hours." at `.agents/skills/managing-obsidian-vault/SKILL.md`

**Verification**:
1. Set up vault with: 2 items in /Needs_Action/ (1 #high added 2 days ago, 1 #medium), 5 items in /Done/
2. Ask Claude: "Update my dashboard"
3. Read Dashboard.md — verify:
   - Pending Actions: 2 items, #high sorted first
   - Recently Completed: 5 items, most recent first
   - Stats: Needs_Action=2, Done=5, all other folders=0
   - Alerts: 1 item (the #high > 24h old)
   - Timestamp: ISO-8601 format
4. Read Logs — verify update_dashboard entry

**Checkpoint**: User Story 3 complete — Dashboard is authoritative state view

---

## Phase 6: User Story 4 — Complete a Task (Priority: P2)

**Goal**: User marks task done. Source file moves to /Done/, Dashboard updates, stats recalculate, completion logged.

**Independent Test**: Place task in /Needs_Action/ with source in /Inbox/. Mark complete. Verify all file movements, Dashboard changes, and log entry.

### Implementation for User Story 4

- [ ] T023 [US4] Verify SKILL.md Section 4 includes complete task lifecycle: (1) move source /Inbox/ → /Done/, (2) move related /Plans/ → /Done/ if any, (3) remove from /Needs_Action/, (4) add to Dashboard Recently Completed, (5) recalculate stats, (6) log with action: complete at `.agents/skills/managing-obsidian-vault/SKILL.md`
- [ ] T024 [US4] Add task identification logic to SKILL.md Section 4: "When user says 'I finished [task]', match against /Needs_Action/ entries by filename or summary text. If ambiguous, list matches and ask user to choose." at `.agents/skills/managing-obsidian-vault/SKILL.md`
- [ ] T025 [US4] Add error handling to SKILL.md Section 4: "If task not found in /Needs_Action/, report to user. If source file already in /Done/, skip move but still update Dashboard and log." at `.agents/skills/managing-obsidian-vault/SKILL.md`

**Verification**:
1. Initialize vault, place urgent-email.md in /Inbox/, run triage (creates /Needs_Action/ entry)
2. Ask Claude: "I finished the urgent invoice task"
3. Verify: urgent-email.md moved to /Done/, /Needs_Action/ entry removed
4. Read Dashboard.md — Pending Actions empty, Recently Completed has 1 item, Stats correct
5. Read Logs — verify "complete" entry with source_file and details

**Checkpoint**: User Story 4 complete — full task lifecycle working

---

## Phase 7: User Story 5 — Review Audit Logs (Priority: P3)

**Goal**: User asks "what happened today?" and gets a readable summary of all vault operations.

**Independent Test**: Perform several operations, then query logs. Verify all actions appear with timestamps.

### Implementation for User Story 5

- [ ] T026 [US5] Add log review procedure to SKILL.md: new Section 7 "Log Review" — read /Logs/YYYY-MM-DD.json, parse JSON array, present entries in human-readable format (timestamp | action | file | result | details) at `.agents/skills/managing-obsidian-vault/SKILL.md`
- [ ] T027 [US5] Add "no log file" handling: "If no log file exists for requested date, report 'No actions recorded for [date].'" at `.agents/skills/managing-obsidian-vault/SKILL.md`

**Verification**:
1. Run full lifecycle (init → triage 3 files → complete 1 task)
2. Ask Claude: "What actions were taken today?"
3. Verify response includes all operations with correct timestamps and details
4. Ask for a date with no log file — verify "No actions recorded" response

**Checkpoint**: User Story 5 complete — full audit visibility

---

## Phase 8: HITL Approval Routing (Cross-cutting)

**Purpose**: Ensure restricted actions are caught and routed to /Pending_Approval/

- [ ] T028 Verify SKILL.md Section 6 (Approval Routing) includes: (1) restricted action keyword list (send email, payment, transfer, post to, delete permanently, contact), (2) create structured approval file, (3) HALT rule — do not proceed, (4) log with action: create at `.agents/skills/managing-obsidian-vault/SKILL.md`
- [ ] T029 Add restricted action detection to triage pipeline in SKILL.md Section 2: "After classifying priority, scan body for restricted action keywords. If found, route to /Pending_Approval/ instead of /Needs_Action/." at `.agents/skills/managing-obsidian-vault/SKILL.md`
- [ ] T030 Verify `references/handbook-template.md` Autonomy Boundaries section matches constitution Principle II exactly: CANNOT list includes send emails, make payments, post social, delete permanently, contact externally, install software, access databases at `.agents/skills/managing-obsidian-vault/references/handbook-template.md`

**Verification**:
1. Place file in /Inbox/ with body: "Please send an email to the client about the overdue payment"
2. Run triage
3. Verify file routed to /Pending_Approval/ (NOT /Needs_Action/)
4. Verify approval request file contains: action needed, context, priority, approve/deny prompt
5. Verify log entry with action: "create", details mentioning restricted action detection
6. Verify /Needs_Action/ does NOT contain this item

**Checkpoint**: HITL routing verified — Bronze Tier safety enforced

---

## Phase 9: Bronze Tier Safety Validation

**Purpose**: Final validation that entire system complies with Bronze Law Constitution

- [ ] T031 [P] Run Bronze Law audit: grep all skill files for external API references (curl, fetch, http, https, request, api.*, smtp, webhook) — confirm zero matches at `.agents/skills/managing-obsidian-vault/`
- [ ] T032 [P] Verify no autonomous loop patterns in SKILL.md: grep for "while", "repeat", "loop", "poll", "watch", "cron", "schedule" — all operations must be human-triggered at `.agents/skills/managing-obsidian-vault/SKILL.md`
- [ ] T033 Run full Green Path end-to-end test:
  1. Initialize empty vault → verify 5 folders + 2 core files
  2. Place 3 test files in /Inbox/ (urgent email, meeting request, newsletter)
  3. Triage → verify 2 in /Needs_Action/, 1 in /Done/
  4. Check Dashboard → 2 pending (#high first), 1 done, correct stats
  5. Mark urgent task complete → verify file moves, Dashboard update
  6. Check final Dashboard → 1 pending, 2 done, stats match
  7. Review audit log → verify all operations logged with correct schema
  8. Place restricted-action file → verify routes to /Pending_Approval/
- [ ] T034 Verify all log entries across entire test run have: valid ISO-8601 timestamps, valid action types, non-empty details with rationale, valid result values

**Checkpoint**: Full Bronze Tier compliance verified

---

## Phase 10: Polish & Documentation

**Purpose**: Final cleanup for submission readiness

- [ ] T035 [P] Add README.md to skill directory with: overview, file structure explanation, installation notes, tests/scenarios.md purpose at `.agents/skills/managing-obsidian-vault/README.md`
- [ ] T036 [P] Add table of contents to `references/log-format.md` (file exceeds 100 lines per review finding) at `.agents/skills/managing-obsidian-vault/references/log-format.md`
- [ ] T037 [P] Add table of contents to `references/handbook-template.md` (file exceeds 100 lines per review finding) at `.agents/skills/managing-obsidian-vault/references/handbook-template.md`
- [ ] T038 Update `tests/scenarios.md` to add Bronze-specific scenario: "Initialize vault with only Bronze Tier folders, triage one email file, verify full lifecycle" at `.agents/skills/managing-obsidian-vault/tests/scenarios.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 — BLOCKS all user stories
- **US1: Vault Init (Phase 3)**: Depends on Phase 2 — BLOCKS US2–US5
- **US2: Inbox Triage (Phase 4)**: Depends on US1 (vault must exist to triage)
- **US3: Dashboard (Phase 5)**: Depends on US2 (needs items to display)
- **US4: Task Completion (Phase 6)**: Depends on US2 (needs triaged items)
- **US5: Audit Review (Phase 7)**: Depends on US2 (needs log data to review)
- **HITL Routing (Phase 8)**: Depends on US2 (extends triage pipeline)
- **Safety Validation (Phase 9)**: Depends on ALL previous phases
- **Polish (Phase 10)**: Depends on Phase 9

### User Story Dependencies

- **US1 (P1)**: Foundation — no dependencies on other stories
- **US2 (P1)**: Depends on US1 (vault must be initialized)
- **US3 (P2)**: Can start after US2 (needs vault data to display)
- **US4 (P2)**: Can start after US2 (needs triaged items to complete)
- **US5 (P3)**: Can start after US2 (needs log data from operations)
- **US3 and US4 can run in parallel** once US2 is complete

### Parallel Opportunities

Within each phase, tasks marked [P] can run in parallel:
- Phase 1: T002, T003, T004 can run in parallel
- Phase 9: T031, T032 can run in parallel
- Phase 10: T035, T036, T037 can run in parallel

### Implementation Strategy

**MVP (minimum viable demo)**: Complete Phases 1–4 (Setup + Logger + US1 + US2)
- This gives: vault init + inbox triage + logging = core Bronze Tier functionality
- Dashboard and task completion (US3, US4) build on the MVP incrementally

**Incremental delivery order**:
1. Phases 1–2: Skill alignment + audit logger
2. Phase 3 (US1): Vault initialization — first demo: "set up my vault"
3. Phase 4 (US2): Inbox triage — second demo: "process my inbox"
4. Phase 5 (US3): Dashboard — third demo: accurate state view
5. Phase 6 (US4): Task completion — fourth demo: full lifecycle
6. Phases 7–10: Audit review, HITL safety, validation, polish
