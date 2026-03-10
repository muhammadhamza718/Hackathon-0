---
description: Create or update the feature specification as a Digital FTE (Gold Tier Autonomous Employee).
handoffs:
    - label: Build Technical Plan
      agent: sp.plan
      prompt: Create a plan for this Gold Tier spec. I am building with...
    - label: Clarify Spec Requirements
      agent: sp.clarify
      prompt: Clarify specification requirements for this FTE task
      send: true
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Outline

You are acting as a **Lead Agent Engineer** specializing in the **Gold Tier: Autonomous Employee** framework. Your goal is to transform a natural language description into a detailed **Digital FTE Specification**.

Follow this execution flow:

1. **Brand the Feature**: Generate a concise short name (2-4 words) for the branch (e.g., "odoo-accounting-audit", "whatsapp-lead-capture").

2. **Branch & File Setup**:
    - Fetch remote branches: `git fetch --all --prune`
    - Calculate the next feature number (check local/remote/specs).
    - Run: `.specify/scripts/bash/create-new-feature.sh --json "$ARGUMENTS" --number N+1 --short-name "short-name"`
    - IMPORTANT: Refer to the JSON output for `BRANCH_NAME` and `SPEC_FILE`.

3. **FTE-First Reasoning**:
   When parsing the description, you MUST analyze it through the **Perception -> Reasoning -> Action** lens:
    - **Perception (Watchers)**: What triggers this task? (Gmail, WhatsApp, Odoo JSON-RPC, Cron, File drops).
    - **Reasoning**: What specific logic determines success? (Revenue thresholds, date logic, pattern matching).
    - **Action (MCP)**: What "Hands" are needed? (Browser for payments, Email MCP, Odoo MCP, Social Media APIs).
    - **Autonomy**: Does this need the **Ralph Wiggum loop**? (Multi-step tasks that need to iterate until a promise like `TASK_DONE` is met).

4. **Detailed Specification Drafting**:
   Use `.specify/templates/spec-template.md` as your base, but enforce these **Gold Tier Standards**:
    - **User Scenarios**: Prioritize by "Business Value". US1 should always be the MVP for the FTE.
    - **FTE Autonomous Layer**: THIS IS MANDATORY.
        - **Watchers**: Specify the Python script class (e.g., `GmailWatcher`) and its `check_interval`.
        - **MCP Capabilities**: Precise list of tools (e.g., `browser-mcp:navigate`, `odoo-rpc:call`).
        - **Sensitive Triggers (HITL)**: Any action involving MONEY (Banking/Payments), SOCIAL POSTS, or CUSTOMER REPLIES must be marked as Human-in-the-Loop.
    - **Success Criteria**: Must be measurable (e.g., "Audit report delivered by 8 AM Monday", "Response time < 30s").
    - **Audit & Security**: Define the logging requirement to `Logs/YYYY-MM-DD.json`.

5. **Validation & Quality**:
    - Create `FEATURE_DIR/checklists/requirements.md` using the standard quality checklist.
    - Ensure NO implementation details (code snippets) in the spec - focus on BEHAVIOR.
    - Limit [NEEDS CLARIFICATION] to max 3 items. Prioritize: 1. Financial Risk, 2. Privacy/Security, 3. Integration Boundaries.

6. **Prompt History Record**:
    - Create a PHR record using `.specify/scripts/bash/create-phr.sh --title "<title>" --stage spec --feature <name> --json`.

## Quick Guidelines

- **Think FTE**: Don't just build a "feature"; hire a "digital employee".
- **Safety First**: If a task mentions payment or social media, the spec MUST include a `/Pending_Approval` workflow.
- **Autonomous Persistence**: Use the Ralph Wiggum pattern for tasks that require deep iteration (e.g., multi-page scraping or complex accounting reconciliation).
- **Proactive Audit**: Include "Proactive Suggestions" as a success criterion where the FTE audits data to find bottlenecks.

---

_Version: 2.0.0 (Gold Tier Edition)_
