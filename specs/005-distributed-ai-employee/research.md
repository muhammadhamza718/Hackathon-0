# Research: Platinum Distributed AI Employee

## Decision 1: Use a capability matrix to enforce Cloud vs Local specialization

**Decision**: Split node responsibilities by capability, with Cloud responsible for continuous perception, Odoo monitoring, and draft generation, and Local responsible for approvals, final execution, secret-bearing sessions, and dashboard authorship.

**Rationale**: The Platinum constitution makes the Cloud node a drafting and monitoring worker, while the Local node remains the execution authority. A capability matrix prevents accidental drift where folder visibility is mistaken for permission to act.

**Alternatives considered**:
- Folder-only permissions: rejected because both nodes still need read access to shared state.
- Local-only execution without cloud perception: rejected because it would not deliver 24/7 operation.
- Cloud execution with selective exceptions: rejected because it conflicts with the Hands Rule and secret isolation.

## Decision 2: Standardize synchronization on pull-rebase-push with ownership-aware preflight rules

**Decision**: Use Git as the primary synchronization loop with preflight validation, node-scoped commits, `fetch`, `pull --rebase`, conflict policy checks, and push. Cloud and Local both run the same sync engine but with different ownership policies.

**Rationale**: Git provides explicit history, deterministic conflict detection, and a shared remote checkpoint for distributed coordination. Rebase preserves a linear operational timeline while still surfacing ownership conflicts instead of hiding them.

**Alternatives considered**:
- Syncthing-only replication: rejected because it provides weaker review and conflict semantics for shared Markdown state.
- Push-only sync: rejected because it increases divergence and makes conflict recovery harder.
- Auto-merge of all Markdown changes: rejected because dashboard, approvals, and active plans have ownership semantics that cannot be merged safely by default.

## Decision 3: Require upstream-confirmed claims before irreversible execution

**Decision**: Treat `/In_Progress/<agent>/` as the local ownership marker, but require the claim move plus claim sidecar to rebase and push successfully before any irreversible step is executed.

**Rationale**: In a distributed system, a local move alone is not enough to prove global ownership. Upstream confirmation makes claims visible to both nodes and turns Git history into the arbitration mechanism for simultaneous claims.

**Alternatives considered**:
- Plain folder move without sync confirmation: rejected because simultaneous claims could lead to duplicate execution under network lag.
- External lock server: rejected because it adds new infrastructure and violates the vault-first design.
- Time-based courtesy delays without claims: rejected because they reduce race likelihood but do not create reliable ownership.

## Decision 4: Keep secret and PII artifacts outside the synchronized vault root

**Decision**: Store `.env`, tokens, cookie jars, browser profiles, WhatsApp sessions, and raw sensitive sidecars in gitignored runtime directories or OS-native secret stores, and allow only sanitized, shareable state into the synchronized vault.

**Rationale**: Platinum requires zero-knowledge synchronization. The cleanest way to enforce this is to keep secret material physically outside the shared path and make sync preflight fail closed on forbidden files.

**Alternatives considered**:
- Encrypt secrets in the repo: rejected because the cloud node would still need decryption access and key handling becomes another secret-sync problem.
- Rely only on `.gitignore`: rejected because operator mistakes can still stage sensitive files without stronger preflight checks.
- Sync full sidecars with partial masking: rejected because many sidecars contain enough context to remain sensitive even after superficial redaction.

## Decision 5: Harden cloud Odoo behind HTTPS, restricted credentials, and operational health checks

**Decision**: Place Odoo behind HTTPS termination, restrict the cloud service account to read and draft-only actions, run automated backups with restore verification, and monitor JSON-RPC health through lightweight authenticated checks.

**Rationale**: Odoo becomes a long-lived cloud dependency in Platinum. That makes transport security, service continuity, and least privilege mandatory. Lightweight heartbeat calls are sufficient to validate readiness without mutating accounting data.

**Alternatives considered**:
- Directly expose Odoo without reverse proxy: rejected because TLS and access control become harder to manage safely.
- Use the same credentials on cloud and local: rejected because it breaks the lower-privilege requirement.
- Skip restore verification for backups: rejected because backup files alone do not prove recoverability.

## Decision 6: Local node owns failover and recovery orchestration

**Decision**: Have both nodes publish heartbeats, but let the Local node interpret cloud staleness, enter temporary single-node mode, and control recovery by forcing the returning cloud node through a sync-only catch-up period.

**Rationale**: The Local node already owns execution authority and the authoritative dashboard. Making it the failover coordinator preserves a single executive control plane and avoids split-brain recovery decisions.

**Alternatives considered**:
- Cloud self-heals without local coordination: rejected because the Local node would not know whether cloud state is safe to trust.
- External supervisor service: rejected because it adds infrastructure outside the vault-first architecture.
- Immediate full-write resumption on cloud return: rejected because stale claims and unsynced drafts could produce conflicting actions.

## Decision 7: Add two first-class Platinum skills before broader expansion

**Decision**: Define `cloud-orchestrator` and `git-sync-manager` as the first mandatory Platinum skills, with `local-executive-control`, `distributed-claim-manager`, and `odoo-health-monitor` as supporting skills.

**Rationale**: The user explicitly asked for clear skill definitions for Cloud orchestration and Git sync. Making them first-class keeps the architecture modular and gives later implementation work stable boundaries.

**Alternatives considered**:
- One monolithic Platinum skill: rejected because synchronization, orchestration, and local execution have different trust boundaries.
- Delay skill boundaries until implementation: rejected because the constitution requires modular Agent Skills and the plan must be decision complete.
