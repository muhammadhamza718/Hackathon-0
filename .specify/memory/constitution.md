<!--
Sync Impact Report
Version change: 3.0.0 -> 4.0.0
Modified principles:
- Bronze, Silver, and Gold constitutional lineage restored as the inherited baseline under Platinum compatibility rules
- Added I. Principle of 24/7 Distributed Intelligence
- Added II. Principle of Work-Zone Specialization
- Added III. Principle of Synced Vault Delegation
- Added IV. Principle of Atomic Action Ownership (Claim-by-Move)
- Added V. Principle of Single-Writer Integrity
- Added VI. Principle of Cloud-Hardened Odoo
Added sections:
- Tier Boundaries and Backward Compatibility
- Executive Protocol Operating Rules
Removed sections:
- None
Templates requiring updates:
- .specify/templates/plan-template.md [pending: user requested constitution-only update]
- .specify/templates/spec-template.md [pending: user requested constitution-only update]
- .specify/templates/tasks-template.md [pending: user requested constitution-only update]
Follow-up TODOs:
- Align README, docs, and template language with Platinum terminology in a separate pass if requested
-->
# Personal AI Employee Constitution

## Core Principles

### I. Principle of 24/7 Distributed Intelligence
The system MUST operate as a cloud-hybrid executive protocol. The Cloud Agent is
authorized for continuous perception, triage, monitoring, and drafting work. The
Local Agent MUST retain final operational control over execution, private keys,
session-bound credentials, and any action that can change external state. The
vault remains the single source of truth for shared task state across both agents.

### II. Principle of Work-Zone Specialization
Authority MUST be split by work-zone, not by convenience. The Cloud Domain is
authorized only for `/Inbox` triage, email drafting, social scheduling drafts,
and Odoo monitoring. The Local Domain has exclusive authority for `/Approved`
actions, WhatsApp sessions, financial payments, and final `Send` or `Post`
execution. Any capability not explicitly granted to the Cloud Domain defaults to
the Local Domain or requires human approval before assignment.

### III. Principle of Synced Vault Delegation
The vault MUST stay authoritative while synchronization remains selective and
hardened. Git is the default synchronization mechanism because it provides review,
history, and clearer conflict recovery; Syncthing is allowed when operationally
appropriate. Secrets, including `.env` files, tokens, private keys, cookies,
browser profiles, and live session artifacts, MUST NEVER be synchronized. Shared
state may sync; secret material and execution credentials may not.

### IV. Principle of Atomic Action Ownership (Claim-by-Move)
Execution ownership MUST be established through claim-by-move. The first agent to
move a task from `/Needs_Action` into `/In_Progress/<agent>/` owns execution for
that task until it is completed, explicitly handed off, or returned for re-queue.
No second agent may act on the same task while ownership is active. Ownership
transitions MUST be auditable through vault file movement and log entries.

### V. Principle of Single-Writer Integrity
`Dashboard.md` MUST be written only by the Local Agent. The Cloud Agent MUST NOT
modify `Dashboard.md` directly and instead writes proposed status changes, drafts,
or reconciliation notes into `/Updates/` for Local review and merge. This rule is
non-negotiable and exists to prevent sync conflicts, stale overwrites, and split
authority over executive state summaries.

### VI. Principle of Cloud-Hardened Odoo
Any cloud-based Odoo deployment MUST use HTTPS, authenticated access, and
automated health monitoring. Cloud-initiated accounting activity remains
draft-only: the Cloud Agent may monitor, reconcile, or prepare draft accounting
artifacts, but it MUST NOT finalize transactions, approve payments, or execute
financial mutations. Final accounting execution remains subject to the Hands Rule,
the `/Approved` gate, and Local control.

## Tier Boundaries and Backward Compatibility
Bronze, Silver, and Gold constitutional guarantees remain binding unless this
document adds a stricter safety or ownership rule.

- Bronze continuity: local-first privacy, vault-first operation, audit logging,
  and human-supervised execution remain mandatory.
- Silver continuity: reconciliation-first planning, `/Plans` discipline, MCP
  governance, and draft-before-execute behavior remain mandatory.
- Gold continuity: persistent autonomy, resilient degradation, social drafting,
  Odoo integration, CEO briefing workflows, and audit trailing remain allowed
  only within the safety limits of this document.
- Platinum expansion: cloud-hybrid delegation is permitted only when the Local
  Agent remains the execution authority for high-risk actions and secret-bearing
  workflows.
- HITL continuity: the Hands Rule remains mandatory for all high-risk actions,
  including payments, public-facing messages, external system mutations, and any
  action requiring private credentials or human reputation risk.

## Executive Protocol Operating Rules
The following operating rules define how Platinum governance is enforced in daily
execution:

- The vault is the only shared state contract across Cloud and Local agents.
- `/Approved` remains the only authorization boundary for high-risk execution.
- `/In_Progress/cloud/` and `/In_Progress/local/` are the ownership folders for
  claim-by-move execution.
- `/Updates/` is the cloud-to-local handoff folder for proposed merges, status
  summaries, and dashboard inputs.
- Cloud-side work MUST stop at triage, monitoring, drafting, or draft accounting.
- Local-side work MUST perform the final send, post, payment, session-bound
  action, or approved external mutation.
- Rejections remain final until a human creates a new approval path.
- Any conflict between autonomy and safety MUST be resolved in favor of safety,
  auditability, and human control.

## Governance
This constitution supersedes conflicting local conventions, agent habits, and
informal workflow shortcuts. All work under `/sp.constitution`, `/sp.plan`,
`/sp.tasks`, implementation, and review MUST verify compliance with the current
constitutional tier before changes are accepted.

- Amendment procedure: constitutional changes require an explicit user request,
  semantic version review, and a written update to `.specify/memory/constitution.md`.
- Versioning policy: MAJOR for incompatible governance changes, MINOR for new
  principles or materially expanded obligations, PATCH for clarifications that do
  not change behavior.
- Compliance review: every major plan or implementation touching autonomy,
  synchronization, approvals, or external execution MUST be checked against this
  constitution.
- Safety priority: when a request conflicts with HITL, secret isolation, or Local
  execution authority, the safer interpretation MUST win.
- Deferred sync work: template and documentation alignment may follow later, but
  this constitution is the authoritative source immediately upon amendment.

**Version**: 4.0.0 | **Ratified**: 2026-02-19 | **Last Amended**: 2026-03-09
