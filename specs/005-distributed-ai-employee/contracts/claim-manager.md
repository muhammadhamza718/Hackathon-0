# Contract: Claim Manager

## Skill

`distributed-claim-manager`

## Purpose

Create, maintain, and reconcile task ownership in `/In_Progress/<agent>/`.

## Inputs

- Task file in `/Needs_Action/`
- Node identity
- Current claim lease settings
- Sync visibility state

## Interface

### `claim_task(task_path, node_id) -> TaskClaim`
Moves the task into the node-specific in-progress folder and writes claim metadata.

### `confirm_claim(task_claim, sync_state) -> TaskClaim`
Transitions a claim from tentative to committed after successful upstream sync.

### `refresh_lease(task_claim) -> TaskClaim`
Extends the claim while work remains active.

### `release_claim(task_claim, outcome) -> TaskClaim`
Releases or completes the claim with audit information.

### `reconcile_claim_conflict(local_claim, remote_claim) -> ConflictRecord`
Selects the winning claim based on upstream-visible ordering and policy.

## Guarantees

- No irreversible execution without an upstream-confirmed claim
- No silent owner overwrite
- Every takeover and release is logged
