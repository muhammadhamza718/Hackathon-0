---
id: 003
title: Establish Platinum Executive Protocol
stage: constitution
date: 2026-03-09
surface: agent
model: gpt-5-codex
feature: none
branch: main
user: muhammadhamza718
command: /sp.constitution
labels: ["constitution", "platinum-tier", "executive-protocol", "cloud-hybrid"]
links:
  spec: null
  ticket: null
  adr: null
  pr: null
files:
  - .specify/memory/constitution.md
  - history/prompts/constitution/003-establish-platinum-executive-protocol.constitution.prompt.md
tests:
  - Validation: no unresolved placeholders
  - Validation: version line matches sync report
  - Validation: dates in ISO format YYYY-MM-DD
  - Validation: HITL and backward compatibility clauses present
---

## Prompt

```text
/sp.constitution "Upgrade to Platinum Tier (v4.0). Establish 'The Executive Protocol' with these core principles:

1. Principle of 24/7 Distributed Intelligence: Transition to a Cloud-Hybrid architecture. The Cloud Agent operates 24/7 for perception (triage) and drafting, while the Local Agent maintains control over execution and private keys.
2. Principle of Work-Zone Specialization:
   - Cloud Domain: Authorized for /Inbox triage, email drafting, social scheduling, and Odoo monitoring.
   - Local Domain: Exclusive authority for /Approved actions, WhatsApp sessions, financial payments, and final 'Send/Post' execution.
3. Principle of Synced Vault Delegation: Use Git or Syncthing for vault synchronization. The vault remains the single source of truth for state, while secrets (.env, tokens) MUST NEVER sync.
4. Principle of Atomic Action Ownership (Claim-by-Move): Implement the /In_Progress/<agent>/ rule. The first agent to move a task from /Needs_Action into its own subfolder 'owns' the execution to prevent double-work.
5. Principle of Single-Writer Integrity: Dashboard.md is exclusively owned and written by the Local Agent to prevent sync conflicts. The Cloud Agent writes updates to /Updates/ for Local merge.
6. Principle of Cloud-Hardened Odoo: Secure the cloud-based Odoo instance with HTTPS and automated health monitoring. Maintain the 'Draft-Only' rule for Cloud-initiated accounting.

Backward compatibility with Gold, Silver, and Bronze principles is required. Maintain the mandatory HITL (Hands Rule) gate for all high-risk actions."

No, You only supposed to create the constitutions

where are you creating the constitutions?
and why are asking to implement the plan
.codex\prompts\sp.constitution.md read this file and its will tell you how to create the constitutions ?

ohh Now maybe you should be able to create the constitutions
```

## Response snapshot

Replaced the placeholder constitution template with a complete Platinum Tier
Executive Protocol at v4.0.0. The new constitution preserves Bronze, Silver, and
Gold guarantees, keeps the Hands Rule mandatory for high-risk actions, assigns
Cloud vs Local authority, and records the user-scoped decision to update only the
constitution plus its required PHR.

## Outcome

- Impact: Constitution upgraded from prior Gold lineage to Platinum v4.0.0.
- Tests: Manual validation only; governance document update.
- Files: Constitution file overwritten and constitution PHR created.
- Next prompts: Optionally align templates and docs with Platinum terminology.
- Reflection: User correction narrowed scope to constitution plus required PHR, so
  propagation edits were intentionally deferred.

## Evaluation notes (flywheel)

- Failure modes observed: `create-phr.sh` failed under the Windows sandbox with an
  access error, so the PHR was created manually from the template.
- Graders run and results (PASS/FAIL): PASS - placeholder scan, version/date
  coherence, and HITL compatibility reviewed manually.
- Prompt variant (if applicable): null
- Next experiment (smallest change to try): Update templates and docs in a
  separate constitution-alignment pass if requested.
