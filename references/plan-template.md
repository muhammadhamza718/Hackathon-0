---
task_id: PLAN-XXXX
source_link: /Inbox/EMAIL_client_example.md
created_date: 2026-02-21T10:30:00Z
priority: high
status: Draft
blocked_reason: null
---

# Objective

Generate and send January invoice to Client A for $1,500.

## Context

Client A requested invoice via WhatsApp. Amount is $1,500 (from rate card).
Dependency: Rate card in /Accounting/Rates.md exists. No external factors blocking.

## Roadmap

- [ ] Identify client: Client A (client_a@example.com)
- [ ] Calculate amount: $1,500 (from /Accounting/Rates.md)
- [ ] Generate invoice PDF
- [ ] ✋ Send email (requires human approval)
- [ ] Log transaction in /Accounting/Current_Month.md

## Reasoning Logs

- 2026-02-21T10:30:00Z Agent: Created plan from WhatsApp message. Objective: Generate and send invoice.
- 2026-02-21T10:35:00Z Agent: Identified rate: $1,500. Completed steps 1-2.
- 2026-02-21T10:40:00Z Agent: Generated invoice PDF in /Invoices/2026-01_Client_A.pdf. Marked step 3 complete.
