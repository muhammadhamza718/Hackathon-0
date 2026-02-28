# ADR-001: Bronze-Silver Tiered Architecture

## Status
Accepted

## Date
2026-01-15

## Context
We needed an architecture for an autonomous AI Employee that can handle both simple vault management tasks and complex multi-step workflows requiring human approval.

### Requirements
- Simple tasks (triage, routing) should execute immediately
- Complex tasks (external actions) need human safety gates
- System must be auditable and resumable across sessions
- No external actions without explicit human consent

## Decision
Adopt a two-tier architecture:

### Bronze Tier
- Handles vault management: inbox triage, file routing, dashboard updates
- No external actions permitted
- Fully autonomous within the vault

### Silver Tier
- Extends Bronze with multi-step reasoning and planning
- Creates structured Plan files in `/Plans/`
- Routes HITL-required steps through `/Pending_Approval/`
- Supports session reconciliation for plan resumption

## Alternatives Considered

### Single-tier with feature flags
- Simpler but harder to enforce safety boundaries
- Risk of accidental external action in simple mode

### Three-tier (Bronze/Silver/Gold)
- Gold tier for fully autonomous external actions
- Rejected: premature — no use case requires unsupervised external actions

## Consequences

### Positive
- Clear safety boundary between tiers
- Bronze tier is simple and low-risk
- Silver tier safety gate prevents unauthorized actions
- Architecture is extensible for future tiers

### Negative
- Two codepaths to maintain
- Silver tier adds complexity (plan management, reconciliation)
- Human must be available for HITL approval
