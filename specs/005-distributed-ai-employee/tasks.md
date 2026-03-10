# Tasks: Platinum Distributed AI Employee

**Input**: Design documents from `/specs/005-distributed-ai-employee/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: No explicit TDD requirement in the spec. Add tests later if needed during implementation.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [ ] T001 Create Platinum package and skill directories in `agents/platinum/__init__.py` and `agents/skills/` (Acceptance Criteria: folders exist, `agents/platinum/__init__.py` imports cleanly)
- [ ] T002 [P] Create Platinum skill skeletons in `agents/skills/platinum_cloud_orchestrator/SKILL.md`, `agents/skills/git_sync_manager/SKILL.md`, `agents/skills/local_executive_control/SKILL.md`, and `agents/skills/distributed_claim_manager/SKILL.md` (Acceptance Criteria: each skill has a stub file and declared purpose)
- [ ] T003 [P] Add shared runtime directories to `.gitignore` (Acceptance Criteria: `.runtime/` and secret-bearing paths are ignored by Git status)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**CRITICAL**: No user story work can begin until this phase is complete

- [ ] T004 Extend tier and folder constants in `agents/constants.py` (Acceptance Criteria: new Platinum tier and folder constants for `In_Progress` and `Updates` are defined without breaking existing tests)
- [ ] T005 [P] Define shared Platinum data models in `agents/platinum/models.py` (Acceptance Criteria: models cover NodeHeartbeat, TaskClaim, SyncState, and ConflictRecord with validation)
- [ ] T006 [P] Add Platinum config loader in `agents/platinum/config.py` (Acceptance Criteria: config loads node role, repo path, and heartbeat settings from environment defaults)
- [ ] T007 Implement sync policy classification in `agents/platinum/sync_policy.py` (Acceptance Criteria: policy returns ownership for `Dashboard.md`, `/Plans/`, `/Approved/`, `/In_Progress/`, and `/Updates/`)
- [ ] T008 Implement claim sidecar serializer in `agents/platinum/claim_manager.py` (Acceptance Criteria: claim metadata can be written and read without ambiguity)
- [ ] T009 Add node identity detection utility in `agents/platinum/utils.py` (Acceptance Criteria: node identity resolves to `cloud` or `local` deterministically)

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Continuous Cloud Perception (Priority: P1) MVP

**Goal**: Cloud node performs always-on perception, Odoo monitoring, and drafting without executing local-only actions.

**Independent Test**: Introduce inbox items and Odoo events while local is offline, then verify drafts and alerts appear in shared vault state.

### Implementation for User Story 1

- [ ] T010 [P] [US1] Implement cloud orchestrator loop in `agents/platinum/cloud_orchestrator.py` (Acceptance Criteria: can scan `/Inbox/` and produce triage artifacts without touching `/Approved/`)
- [ ] T011 [P] [US1] Implement heartbeat publisher in `agents/platinum/heartbeat_monitor.py` (Acceptance Criteria: emits heartbeat JSON to `/Updates/heartbeats/` with timestamp and node id)
- [ ] T012 [P] [US1] Implement Odoo health monitor in `agents/platinum/odoo_health_monitor.py` (Acceptance Criteria: performs HTTPS JSON-RPC heartbeat without write calls)
- [ ] T013 [US1] Integrate Odoo draft creation flow with `agents/gold/odoo_rpc_client.py` (Acceptance Criteria: creates draft package in vault without final mutation)
- [ ] T014 [US1] Enforce cloud boundary checks in `agents/platinum/cloud_orchestrator.py` (Acceptance Criteria: any local-only action is logged as deferred and not executed)

**Checkpoint**: Cloud perception and draft flows work independently without local execution.

---

## Phase 4: User Story 2 - Local Executive Control (Priority: P2)

**Goal**: Local node remains the only executor for approvals, payments, and identity-bound actions.

**Independent Test**: Place approved items in `/Approved/` and verify only local execution occurs while cloud refuses.

### Implementation for User Story 2

- [ ] T015 [P] [US2] Implement local executive router in `agents/platinum/local_executive.py` (Acceptance Criteria: consumes `/Approved/` items and executes via existing gates)
- [ ] T016 [US2] Integrate HITL gating and audit logging in `agents/platinum/local_executive.py` (Acceptance Criteria: execution is blocked without approval and audit entry is created)
- [ ] T017 [US2] Implement local-only action allowlist in `agents/platinum/local_executive.py` (Acceptance Criteria: WhatsApp, payment, and final send/post paths are enforced locally)

**Checkpoint**: Local-only execution boundary is enforced end-to-end.

---

## Phase 5: User Story 3 - Reliable Shared Vault Synchronization (Priority: P3)

**Goal**: Cloud and Local synchronize via Git with deterministic conflict handling and secret isolation.

**Independent Test**: Change shared state on both nodes, run sync, and verify conflicts are resolved or surfaced while secrets never sync.

### Implementation for User Story 3

- [ ] T018 [P] [US3] Implement sync preflight in `agents/platinum/git_sync_manager.py` (Acceptance Criteria: blocked when excluded paths or forbidden files are staged)
- [ ] T019 [P] [US3] Implement pull-rebase-push flow in `agents/platinum/git_sync_manager.py` (Acceptance Criteria: successful sync produces a single rebased commit and records sync state)
- [ ] T020 [US3] Implement conflict resolution rules in `agents/platinum/git_sync_manager.py` using `agents/platinum/sync_policy.py` (Acceptance Criteria: `Dashboard.md` stays local-owned and plan conflicts are diverted to `/Updates/`)
- [ ] T021 [US3] Add sync state emitter in `agents/platinum/git_sync_manager.py` (Acceptance Criteria: writes sync metrics to `/Updates/sync/<node>.json`)
- [ ] T022 [US3] Extend `.gitignore` and sync exclusion list for secret sidecars in `.gitignore` and `agents/platinum/sync_policy.py` (Acceptance Criteria: secret-bearing files never appear in staged changes)

**Checkpoint**: Sync pipeline is deterministic and excludes secrets by policy.

---

## Phase 6: User Story 4 - Distributed Ownership and Visibility (Priority: P4)

**Goal**: Task ownership, node health, and sync freshness are visible in the local dashboard.

**Independent Test**: Claim tasks from both nodes and verify dashboard shows ownership, heartbeat freshness, and sync lag.

### Implementation for User Story 4

- [ ] T023 [P] [US4] Implement claim lifecycle in `agents/platinum/claim_manager.py` (Acceptance Criteria: claims move through tentative, committed, active, and completed states)
- [ ] T024 [US4] Implement claim conflict reconciliation in `agents/platinum/claim_manager.py` (Acceptance Criteria: loser claim is moved to `/Updates/conflicts/` and no double-execution occurs)
- [ ] T025 [P] [US4] Implement dashboard federation in `agents/platinum/dashboard_federator.py` (Acceptance Criteria: merges heartbeats and sync metrics into a local summary)
- [ ] T026 [US4] Extend `agents/dashboard_writer.py` to render distributed status (Acceptance Criteria: `Dashboard.md` includes cloud and local health plus sync lag)
- [ ] T027 [US4] Add outage detection in `agents/platinum/heartbeat_monitor.py` (Acceptance Criteria: stale cloud heartbeat marks node as degraded and triggers local single-node mode flag)

**Checkpoint**: Dashboard reflects ownership, health, and sync freshness from both nodes.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T028 [P] Document Platinum runtime layout in `specs/005-distributed-ai-employee/quickstart.md` (Acceptance Criteria: quickstart covers cloud/local runtime folders and secret isolation)
- [ ] T029 Add distributed audit events to `agents/gold/audit_gold.py` (Acceptance Criteria: claim, sync, and heartbeat events are logged with rationale)
- [ ] T030 Run quickstart validation steps from `specs/005-distributed-ai-employee/quickstart.md` (Acceptance Criteria: manual validation checklist is fully satisfied)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3+)**: All depend on Foundational phase completion
- **Polish (Final Phase)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational - No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational - Depends on US1 outputs for shared drafts
- **User Story 3 (P3)**: Can start after Foundational - Depends on shared models and sync policy
- **User Story 4 (P4)**: Can start after Foundational - Uses claim manager and heartbeat data

### Parallel Opportunities

- Setup tasks marked [P] can run in parallel
- Foundational tasks T005, T006, T007 can run in parallel
- US1 tasks T010, T011, T012 can run in parallel
- US3 tasks T018, T019 can run in parallel
- US4 tasks T023, T025 can run in parallel

---

## Parallel Example: User Story 1

```bash
Task: "Implement cloud orchestrator loop in agents/platinum/cloud_orchestrator.py"
Task: "Implement heartbeat publisher in agents/platinum/heartbeat_monitor.py"
Task: "Implement Odoo health monitor in agents/platinum/odoo_health_monitor.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational
3. Complete Phase 3: User Story 1
4. Validate US1 independently

### Incremental Delivery

1. Add User Story 2 after US1 validation
2. Add User Story 3 after US2 validation
3. Add User Story 4 after US3 validation
4. Finish Polish phase

---

## Notes

- [P] tasks = different files, no dependencies
- Each task line includes explicit acceptance criteria
- Each user story remains independently testable



