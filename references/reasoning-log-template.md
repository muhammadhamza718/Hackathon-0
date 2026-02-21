# Reasoning Log Entry Template

## Purpose

Reasoning Log entries are immutable, timestamped records of agent decisions and actions within a Plan.md file. They create an audit trail enabling humans to understand exactly why the agent took each step.

## Entry Format

```
- [ISO-8601-TIMESTAMP] Agent: [ACTION] — [RATIONALE]
```

**Components**:
- **ISO-8601 Timestamp**: `YYYY-MM-DDTHH:MM:SSZ` (UTC, seconds precision)
- **Actor**: Always "Agent" for Silver Tier
- **Action**: What was done (past tense, concise)
- **Rationale**: Why it was done (brief explanation connecting to plan context)

## Examples

### Step Completion

```
- [2026-02-21T10:35:00Z] Agent: Marked step 2 complete — Identified client rate: $1,500 from /Accounting/Rates.md. Prerequisite met for invoice generation.
```

### External Action Drafted

```
- [2026-02-21T10:45:00Z] Agent: Drafted email for approval — Invoice PDF ready; awaiting human approval before sending via MCP email server.
```

### Block Detected

```
- [2026-02-21T10:45:00Z] Agent: Detected block at step 4 — Approval request created in /Pending_Approval/. Plan status: Blocked: Awaiting Human Approval.
```

### Approval Received & Execution

```
- [2026-02-21T11:00:00Z] Agent: Detected approval received — Email approval file moved to /Approved/. Proceeding with MCP email send.
- [2026-02-21T11:05:00Z] Agent: Executed external action — Email sent to client_a@example.com. Status confirmed by MCP server.
```

### Plan Completion

```
- [2026-02-21T11:10:00Z] Agent: Plan completed — All 5 steps done. Moving plan to /Done/Plans/. Status: Complete.
```

### Error Handling

```
- [2026-02-21T11:06:00Z] Agent: Error detected — MCP email server offline. Email approval moved back to /Pending_Approval/ with failure reason: "Connection timeout". Human can retry when service recovers.
```

### Skipped Steps (if applicable)

```
- [2026-02-21T10:50:00Z] Agent: Step skipped — Logging step 5 not needed; previous transaction already logged. Moving to plan completion.
```

---

## Logging Guidelines

### DO

✅ Include timestamp for every entry (enables chronological ordering)
✅ Use past tense (what happened, not what will happen)
✅ Cite specific file paths or references (enables traceability)
✅ Explain decision context (so humans understand the reasoning)
✅ Record errors and recovery steps (audit trail for debugging)

### DON'T

❌ Omit timestamps (breaks chronology)
❌ Use future tense ("will send", "should complete")
❌ Be vague ("did something", "worked fine")
❌ Include sensitive data (passwords, tokens, PII)
❌ Use non-ISO-8601 timestamps (breaks parsing)

---

## Integration in Plan.md

Reasoning Logs live in the `## Reasoning Logs` section of Plan.md:

```markdown
## Reasoning Logs

- [2026-02-21T10:30:00Z] Agent: Created plan from WhatsApp message. Objective: Generate and send invoice.
- [2026-02-21T10:35:00Z] Agent: Identified rate: $1,500. Completed steps 1-2.
- [2026-02-21T10:40:00Z] Agent: Generated invoice PDF. Marked step 3 complete.
- [2026-02-21T10:45:00Z] Agent: Drafted email for approval. Plan now blocked.
- [2026-02-21T11:00:00Z] Agent: Approval detected. Executing email send.
- [2026-02-21T11:05:00Z] Agent: Email sent. All steps complete. Plan finished.
```

---

## Append-Only Nature

Reasoning Logs are **append-only**:
- Never delete entries
- Never modify timestamps
- Never reorder entries
- Entries create permanent audit trail

When a plan moves to `/Done/Plans/`, the logs are preserved in full for historical review.

---

## Machine Parsing

Reasoning Logs follow a predictable format to enable:
- Automated parsing (regex matching: `- \[[0-9T:-]+Z\] Agent: (.*)`)
- Timestamp extraction
- Action categorization (marked, drafted, detected, executed, error, etc.)
- Traceability linking

