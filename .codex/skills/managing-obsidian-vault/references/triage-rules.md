# Triage Rules

Priority classification logic for inbox items.

## Priority Keywords

### High Priority (`#high`)
Match any of these keywords (case-insensitive) in subject, body, or frontmatter:
- `urgent`, `asap`, `immediately`, `critical`, `emergency`
- `payment`, `invoice`, `overdue`, `past due`, `billing`
- `deadline`, `due today`, `due tomorrow`, `expires`
- `error`, `failure`, `down`, `outage`, `broken`
- `security`, `breach`, `compromised`
- `legal`, `compliance`, `regulatory`

### Medium Priority (`#medium`)
Match any of these keywords when no high-priority keywords are present:
- `review`, `feedback`, `update`, `follow up`, `follow-up`
- `meeting`, `schedule`, `appointment`, `calendar`
- `request`, `proposal`, `quote`, `estimate`
- `question`, `clarification`, `help`
- `report`, `summary`, `status`

### Low Priority (`#low`)
Applied when:
- No high or medium keywords match
- Content is informational only (newsletters, FYI, notifications)
- File type is `file_drop` with no actionable content

## Classification Logic

```
1. Read file content and frontmatter
2. Extract all text (subject + body)
3. Check against HIGH keywords → if match → #high
4. Check against MEDIUM keywords → if match → #medium
5. Default → #low
6. Override: Company_Handbook.md rules take precedence
```

## Actionable vs. Informational

**Actionable** (→ `/Needs_Action/`):
- Contains a request, question, or task
- Requires a response or follow-up
- Has a deadline or time constraint
- Involves a financial transaction
- Needs a decision

**Examples of actionable items:**
- "Please review the Q1 report by Friday" → actionable (#medium, has deadline)
- "URGENT: Invoice #1234 is overdue" → actionable (#high, financial + deadline)
- "Can we schedule a meeting next week?" → actionable (#medium, request)
- "What's the status of Project X?" → actionable (#medium, question)

**Informational** (→ `/Done/`):
- FYI / notification only
- Newsletter or digest
- Confirmation of completed action
- Read receipt or acknowledgment
- No response or action needed

**Examples of informational items:**
- "Weekly Tech Roundup — No action required" → informational (#low)
- "FYI: Office will be closed Monday" → informational (#low)
- "Your order has shipped" → informational (#low, confirmation)
- "Meeting notes from yesterday's standup" → informational (#low, FYI)

## Frontmatter Type Handling

### `type: email`
- Check `from:` field for known VIP contacts (if defined in Handbook)
- Check `subject:` for priority keywords first, then body
- VIP sender + any priority = bump to `#high`

### `type: whatsapp`
- Typically shorter messages, scan full body
- Group messages: look for @mentions of user
- Media references: note as attachment, classify by text content

### `type: file_drop`
- No sender context, rely entirely on content analysis
- Check filename for clues (e.g., `invoice_*.pdf` → `#high`)
- If file is non-markdown (PDF, image): create a summary note, tag `#medium`

### No frontmatter
- Treat as `type: file_drop`
- Log warning: `"No frontmatter found in FILENAME, treating as file_drop"`
- Continue processing normally

### Malformed file
- Cannot be read or parsed
- Log error: `"Malformed file: FILENAME — REASON"`
- Skip file, do not move it
- Add to Dashboard Alerts section

## Priority Override Rules

Always check `Company_Handbook.md` before finalizing priority:
1. Handbook may define custom VIP contacts → auto `#high`
2. Handbook may define blocked senders → auto `#low` + flag
3. Handbook may redefine keyword lists
4. Handbook rules always override default keyword matching
