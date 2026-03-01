# ADR-002: HITL Safety Gate Design

## Status
Accepted

## Date
2026-02-15

## Context
The Silver Tier agent needs to perform external actions (emails, API calls, payments) but we must prevent unsanctioned actions. We need a mechanism to block execution until a human reviews and approves.

## Decision
Implement a file-system-based HITL gate using the Obsidian Vault directory structure:

1. Agent creates a request file in `/Pending_Approval/`
2. Agent blocks and polls for a decision
3. Human moves the file to `/Approved/` or `/Rejected/`
4. Agent detects the decision and proceeds or halts

### Key Design Choices
- **File-based, not API-based**: Uses the vault as the communication channel
- **No auto-approval**: Items never time out to "approved"
- **Immutable after rejection**: Rejected items are not retried
- **Append-only audit log**: Every gate interaction is logged

## Alternatives Considered

### Slack/Discord approval bot
- More interactive but adds external dependency
- Breaks the "vault as single source of truth" principle

### CLI prompt
- Requires agent and human to be in same session
- Doesn't work for async workflows

### Timeout-based auto-approve
- Rejected: violates zero-tolerance safety policy

## Consequences

### Positive
- Zero risk of unauthorized external actions
- Full audit trail in vault
- Works with any Obsidian client (desktop, mobile)
- No external dependencies

### Negative
- Human must manually move files (friction)
- No real-time notification to human
- Polling adds latency to approval flow
