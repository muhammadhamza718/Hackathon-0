# Security Model

## HITL Safety Gate

The Silver Tier agent uses a **Human-In-The-Loop (HITL)** safety gate to prevent unsanctioned external actions.

### Zero Tolerance Policy

**No external action is ever executed without explicit human approval.**

This includes:
- Sending emails
- Making API calls
- Processing payments
- Modifying external systems
- Publishing or sharing data

### Approval Flow

```
Agent detects external action needed
  → Creates approval request in /Pending_Approval/
  → BLOCKS execution
  → Human reviews the request
  → Moves to /Approved/ or /Rejected/
  → Agent checks decision and proceeds (or halts)
```

### Safety Guarantees

1. **No autonomous external actions** — The agent cannot bypass the HITL gate
2. **Audit trail** — Every action is logged in `/Logs/` with timestamps
3. **Explicit approval required** — File must physically exist in `/Approved/`
4. **Rejection is permanent** — Rejected actions are not retried
5. **Timeout safety** — Pending items do not auto-approve

### Threat Model

| Threat | Mitigation |
|--------|-----------|
| Agent sends email without approval | HITL gate blocks all external actions |
| Approval forged | File system permissions on vault |
| Agent modifies own approval | Agent has no write access to Approved/ |
| Action replayed | Each approval file is consumed (moved to Done) |

### Secrets Management

- Never hardcode secrets or tokens
- Use `.env` files (excluded from git via `.gitignore`)
- Document required environment variables in `.env.example`
