# Test Scenarios: managing-obsidian-vault

## Scenario: Initialize Empty Vault

**Difficulty:** Easy

**Query:** "Set up my AI employee vault from scratch in this directory"

**Expected behaviors:**

1. Create folder structure
   - **Minimum:** All 7 folders created (Inbox, Needs_Action, Done, Plans, Pending_Approval, Approved, Logs)
   - **Quality criteria:** Folders created in a single operation, no partial state left on error
   - **Haiku pitfall:** May forget Approved or Logs folders
   - **Weight:** 5

2. Create Dashboard.md
   - **Minimum:** File exists with at least Pending Actions and Stats sections
   - **Quality criteria:** All 4 sections present (Pending Actions, Recently Completed, Stats, Alerts) with empty-state messages and ISO-8601 timestamp
   - **Haiku pitfall:** May use relative timestamps instead of ISO-8601
   - **Weight:** 4

3. Create Company_Handbook.md
   - **Minimum:** File exists with priority definitions and autonomy boundaries
   - **Quality criteria:** All sections present (Communication, Priority Definitions, Approval Thresholds, Autonomy Boundaries) with Bronze Tier restrictions
   - **Haiku pitfall:** May omit autonomy tier restrictions or approval thresholds
   - **Weight:** 4

4. Run health check
   - **Minimum:** Reports that vault is initialized
   - **Quality criteria:** Explicitly verifies each folder and file, reports count (7 folders + 2 files = 9 items verified)
   - **Haiku pitfall:** May skip verification step entirely
   - **Weight:** 3

5. Write audit log
   - **Minimum:** Log entry exists for the creation action
   - **Quality criteria:** Log file at /Logs/YYYY-MM-DD.json with valid JSON array and action: "create"
   - **Haiku pitfall:** May forget to create the log entry for initialization itself
   - **Weight:** 3

---

## Scenario: Triage Three Inbox Files

**Difficulty:** Medium

**Setup:** Vault is initialized. Three files exist in /Inbox/:

```markdown
# File 1: Inbox/urgent-client-email.md
---
type: email
from: Important Client
date: 2026-02-19
subject: URGENT - Invoice payment overdue
---
Please process the overdue invoice #1234 immediately. Payment was due last week.
```

```markdown
# File 2: Inbox/meeting-request.md
---
type: email
from: Team Lead
date: 2026-02-19
subject: Schedule review meeting
---
Can we schedule a review meeting for next week? Need to discuss Q1 plans.
```

```markdown
# File 3: Inbox/weekly-newsletter.md
---
type: email
from: Industry News
date: 2026-02-19
subject: Weekly Tech Roundup
---
Here's your weekly summary of tech news. No action required.
```

**Query:** "Process my inbox"

**Expected behaviors:**

1. Read Company_Handbook.md first
   - **Minimum:** Reads handbook before processing any files
   - **Quality criteria:** Explicitly references handbook priority definitions in triage logic
   - **Haiku pitfall:** May skip handbook check entirely and use defaults
   - **Weight:** 4

2. Classify File 1 as #high
   - **Minimum:** Identified as high priority
   - **Quality criteria:** Cites keywords "urgent" and "invoice payment overdue", creates Needs_Action entry
   - **Haiku pitfall:** May classify as #medium despite multiple high-priority keywords
   - **Weight:** 5

3. Classify File 2 as #medium
   - **Minimum:** Identified as medium priority
   - **Quality criteria:** Cites keywords "schedule" and "meeting", creates Needs_Action entry
   - **Haiku pitfall:** May classify as #low (it's actionable, not informational)
   - **Weight:** 4

4. Classify File 3 as informational
   - **Minimum:** Moved to /Done/ (not Needs_Action)
   - **Quality criteria:** Correctly identifies "No action required" and newsletter pattern, moves to Done
   - **Haiku pitfall:** May create unnecessary Needs_Action entry for informational content
   - **Weight:** 4

5. Update Dashboard
   - **Minimum:** Dashboard reflects 2 pending items, 1 done
   - **Quality criteria:** Pending Actions sorted #high first, Stats show correct counts, timestamp updated
   - **Haiku pitfall:** May not sort by priority or may show stale counts
   - **Weight:** 4

6. Write audit log entries
   - **Minimum:** At least 3 triage entries in log
   - **Quality criteria:** One entry per file + one update_dashboard entry, all with correct action types and results
   - **Haiku pitfall:** May write a single log entry for all three files
   - **Weight:** 3

---

## Scenario: Full Lifecycle

**Difficulty:** Hard

**Setup:** Vault initialized, File 1 from medium scenario is in Needs_Action as #high.

**Query sequence:**
1. "Process my inbox" (with File 2 and File 3 from medium scenario)
2. "I finished the urgent invoice task"
3. "Show me the current status"

**Expected behaviors:**

1. Triage new inbox items
   - **Minimum:** File 2 → Needs_Action, File 3 → Done
   - **Quality criteria:** Correct priority assignment, proper formatting, audit logged
   - **Haiku pitfall:** May re-process already-triaged items
   - **Weight:** 4

2. Complete the invoice task
   - **Minimum:** Source moved to Done, removed from Dashboard Pending
   - **Quality criteria:** Source file Inbox→Done, Needs_Action entry removed, Recently Completed updated, Stats recalculated, audit log entry with action "complete"
   - **Haiku pitfall:** May forget to move source file or update multiple Dashboard sections
   - **Weight:** 5

3. Dashboard accuracy after completion
   - **Minimum:** Shows 1 pending, 2 done
   - **Quality criteria:** Pending Actions has only meeting request, Recently Completed shows invoice + newsletter, Stats match actual counts, no stale data
   - **Haiku pitfall:** May show cached/stale counts instead of recounting
   - **Weight:** 5

4. Audit trail completeness
   - **Minimum:** Log has entries for triage + complete actions
   - **Quality criteria:** Chronological entries covering: 2 triages, 2 dashboard updates, 1 completion — all with correct timestamps, actions, and results
   - **Haiku pitfall:** May have gaps in the audit trail or duplicate entries
   - **Weight:** 4

---

## Scenario: Malformed Inbox File

**Difficulty:** Edge-case

**Setup:** Vault initialized. One file in /Inbox/:

```markdown
# File: Inbox/broken-file.md
This file has no frontmatter at all.
It's just raw text with some content.
Maybe it mentions something urgent but has no structure.
There's an invoice reference here too.
```

**Query:** "Process my inbox"

**Expected behaviors:**

1. Handle missing frontmatter gracefully
   - **Minimum:** File is processed (not crashed, not silently skipped)
   - **Quality criteria:** Treats as file_drop type, logs warning about missing frontmatter, continues processing
   - **Haiku pitfall:** May throw error and stop processing entirely
   - **Weight:** 5

2. Still perform keyword analysis
   - **Minimum:** Attempts to classify by content
   - **Quality criteria:** Scans body text for priority keywords, finds "urgent" and "invoice", classifies as #high
   - **Haiku pitfall:** May default to #low without scanning body text
   - **Weight:** 4

3. Log the warning
   - **Minimum:** Some indication in logs that frontmatter was missing
   - **Quality criteria:** Log entry with result "warning" and details explaining no frontmatter found, treated as file_drop
   - **Haiku pitfall:** May log as success with no mention of the anomaly
   - **Weight:** 4

4. Update Dashboard
   - **Minimum:** Dashboard updated with the new item
   - **Quality criteria:** Item appears in Pending Actions (if actionable) or Stats reflect move to Done
   - **Haiku pitfall:** May skip dashboard update due to the warning
   - **Weight:** 3

**Output validation:**
- Pattern: `warning|file_drop|no frontmatter` in log file
- Dashboard.md updated timestamp within current session
