# Data Model: Platinum Distributed AI Employee

## 1. NodeHeartbeat

**Purpose**: Represents the current health and operating mode of a node.

| Field | Type | Description | Validation |
|---|---|---|---|
| `node_id` | string | Stable identifier such as `cloud` or `local` | Required; unique per node |
| `role` | enum | `cloud`, `local`, `recovering` | Required |
| `status` | enum | `healthy`, `degraded`, `offline`, `recovering` | Derived from freshness and failure signals |
| `last_seen_at` | datetime | Last successful heartbeat publish time | Must be ISO-8601 UTC |
| `last_sync_at` | datetime | Last successful sync time | Must be ISO-8601 UTC |
| `queue_counts` | object | Snapshot of owned or visible work counts | Non-negative values |
| `odoo_status` | enum | `healthy`, `degraded`, `down`, `unknown` | Required for cloud node |
| `notes` | string | Human-readable status note | Optional |

**State transitions**:
- `healthy -> degraded` when heartbeat freshness exceeds warning threshold.
- `degraded -> offline` when stale threshold is exceeded.
- `offline -> recovering` when node returns and begins sync-only catch-up.
- `recovering -> healthy` after sync convergence and conflict-free ownership state.

## 2. TaskClaim

**Purpose**: Represents ownership of a task after claim-by-move.

| Field | Type | Description | Validation |
|---|---|---|---|
| `task_id` | string | Stable task identifier or filename stem | Required |
| `owner_node` | enum | `cloud` or `local` | Required |
| `claim_nonce` | string | Unique claim attempt identifier | Required; immutable |
| `claimed_at` | datetime | When ownership began | Must be ISO-8601 UTC |
| `lease_expires_at` | datetime | When the claim may be treated as stale | Must be later than `claimed_at` |
| `state` | enum | `tentative`, `committed`, `active`, `released`, `completed`, `stale`, `taken_over` | Required |
| `source_path` | string | Original task path before move | Required |
| `current_path` | string | Current `/In_Progress/<agent>/...` location | Required |
| `last_heartbeat_at` | datetime | Last lease refresh time | Optional until active |

**State transitions**:
- `tentative -> committed` after successful rebase and push.
- `committed -> active` when execution begins.
- `active -> completed` when work finishes.
- `active -> released` when returned to queue by owner.
- `active -> stale` when lease expires without refresh.
- `stale -> taken_over` when another node reclaims with audit trail.

## 3. SyncState

**Purpose**: Captures the result of a node's most recent synchronization cycle.

| Field | Type | Description | Validation |
|---|---|---|---|
| `node_id` | string | Node performing sync | Required |
| `sync_started_at` | datetime | Start of sync cycle | Required |
| `sync_finished_at` | datetime | End of sync cycle | Optional until completion |
| `result` | enum | `success`, `conflict`, `blocked`, `failed` | Required |
| `ahead_count` | integer | Local commits ahead before push | Non-negative |
| `behind_count` | integer | Remote commits behind before rebase | Non-negative |
| `conflicted_files` | array | Files requiring review | Empty when `result=success` |
| `excluded_paths_detected` | array | Forbidden paths found during preflight | Empty when compliant |
| `latency_seconds` | number | Age of last successful sync compared with now | Non-negative |

**State transitions**:
- `success -> blocked` when preflight finds excluded files.
- `success -> conflict` when rebase detects ownership collisions.
- `conflict -> success` after explicit resolution and clean rerun.
- `failed -> recovering` is represented operationally by a follow-up sync attempt.

## 4. ApprovalArtifact

**Purpose**: Represents a draft or approval-ready action produced by Cloud or Local.

| Field | Type | Description | Validation |
|---|---|---|---|
| `artifact_id` | string | Unique approval record id | Required |
| `origin_node` | enum | `cloud` or `local` | Required |
| `action_type` | enum | `email`, `social_post`, `payment`, `odoo_draft`, `message`, `other` | Required |
| `state` | enum | `drafted`, `pending_approval`, `approved`, `rejected`, `executed` | Required |
| `risk_level` | enum | `low`, `medium`, `high` | Required |
| `requires_local_execution` | boolean | Whether final action must be local | Always true for high-risk actions |
| `approved_at` | datetime | Approval timestamp | Required once approved |
| `executed_by` | string | Node that executed the action | Must be `local` for high-risk actions |

**State transitions**:
- `drafted -> pending_approval` when routed for HITL.
- `pending_approval -> approved` or `rejected` by human action.
- `approved -> executed` only after local claim and execution.

## 5. AccountingDraft

**Purpose**: Represents a cloud-prepared accounting package for local review.

| Field | Type | Description | Validation |
|---|---|---|---|
| `draft_id` | string | Unique Odoo draft identifier | Required |
| `trigger_event` | string | Business event that caused the draft | Required |
| `odoo_model` | string | Target accounting object | Required |
| `draft_summary` | string | Human-readable summary of proposed change | Required |
| `evidence_refs` | array | Related vault files or monitored records | At least one reference |
| `prepared_by` | string | Usually `cloud` | Required |
| `approval_state` | enum | `drafted`, `pending_approval`, `approved`, `rejected`, `executed` | Required |
| `execution_receipt` | string | Local execution result or record reference | Optional until executed |

**State transitions**:
- `drafted -> pending_approval` after packaging.
- `pending_approval -> approved` or `rejected` by human action.
- `approved -> executed` only through local execution.

## 6. ConflictRecord

**Purpose**: Stores unresolved or policy-resolved synchronization conflicts.

| Field | Type | Description | Validation |
|---|---|---|---|
| `conflict_id` | string | Unique conflict identifier | Required |
| `file_path` | string | Conflicted file path | Required |
| `conflict_type` | enum | `dashboard`, `plan`, `claim`, `approval`, `generic_markdown` | Required |
| `winning_node` | enum | `cloud`, `local`, `manual_review`, `none` | Required |
| `losing_node` | enum | `cloud`, `local`, `none` | Optional |
| `resolution_state` | enum | `open`, `policy_resolved`, `manual_review`, `closed` | Required |
| `recorded_at` | datetime | Time of conflict detection | Required |
| `notes` | string | Reason for resolution outcome | Required |

## 7. ExecutiveDashboardState

**Purpose**: The local-authored summary of distributed operations shown in `Dashboard.md`.

| Field | Type | Description | Validation |
|---|---|---|---|
| `cloud_heartbeat` | NodeHeartbeat | Cloud node status | Required |
| `local_heartbeat` | NodeHeartbeat | Local node status | Required |
| `sync_state_cloud` | SyncState | Latest cloud sync summary | Required |
| `sync_state_local` | SyncState | Latest local sync summary | Required |
| `active_claims` | array<TaskClaim> | Tasks currently owned across nodes | Must match vault state |
| `approval_backlog` | integer | Count of items awaiting approval or execution | Non-negative |
| `alerts` | array | Human-visible distributed warnings | Empty when healthy |
| `last_merged_update_at` | datetime | When Local last merged `/Updates/` | Required |

## Relationships

- `ExecutiveDashboardState` aggregates `NodeHeartbeat`, `SyncState`, and `TaskClaim`.
- `ApprovalArtifact` and `AccountingDraft` may both reference a `TaskClaim` when execution is underway.
- `ConflictRecord` may reference `TaskClaim`, `SyncState`, or `ExecutiveDashboardState` depending on the conflict type.
- `NodeHeartbeat` and `SyncState` share the same `node_id` and are merged to determine node operating status.

## Validation Rules

- A task may have at most one `active` or `committed` `TaskClaim` across all nodes.
- `ApprovalArtifact.executed_by` must be `local` whenever `risk_level=high` or the action type is in the local-only set.
- `Dashboard.md` may only be generated from `ExecutiveDashboardState` on the Local node.
- Any sync cycle that detects excluded secret paths must end in `blocked` and produce no push.
- A cloud node may create `AccountingDraft` records but may not mark them `executed`.
