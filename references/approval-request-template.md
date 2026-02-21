---
action_type: email
target_recipient: client_a@example.com
approval_required_by: human
rationale: "Plan PLAN-2026-001, Step 4: Send invoice to Client A for $1,500"
created_date: 2026-02-21T10:45:00Z
status: pending
plan_id: PLAN-2026-001
step_id: 4
step_description: "Send email with invoice attachment"
---

# Email Approval Request

## Action Details

- **Type**: Email Send
- **To**: client_a@example.com
- **Subject**: January 2026 Invoice - $1,500
- **Plan Reference**: PLAN-2026-001, Step 4/5
- **Created**: 2026-02-21T10:45:00Z

## Draft Content

```
Dear Client A,

Please find attached your invoice for January 2026 services.

Invoice Details:
- Amount: $1,500.00
- Period: January 1-31, 2026
- Reference: INV-2026-001

Please remit payment to:
[Bank Details from Company_Handbook.md]

Thank you for your business!

Best regards,
[Your Company Name]
```

## Rationale

This email is required to deliver the invoice to the client as part of the plan to generate and send January invoices. The invoice PDF has been verified and is ready for delivery.

## Human Action Required

- **To Approve & Execute**: Move this file to `/Approved/`
- **To Reject & Halt**: Move this file to `/Rejected/`

The agent will automatically detect the file move and proceed accordingly.

---

**IMPORTANT**: Do NOT modify the YAML frontmatter. The agent reads these fields to confirm approval status and routing.

