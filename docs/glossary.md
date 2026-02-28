# Glossary

| Term | Definition |
|------|-----------|
| **Bronze Tier** | Base tier handling vault management, inbox triage, and dashboard updates. No external actions. |
| **Silver Tier** | Advanced tier with multi-step reasoning, plan persistence, and HITL approval gates. |
| **FTE** | Full-Time Employee — the AI agent operating as an autonomous digital worker. |
| **HITL** | Human-In-The-Loop — safety mechanism requiring human approval before external actions. |
| **Vault** | The Obsidian Vault used as the single source of truth for all agent operations. |
| **Sentinel** | File system watcher component that monitors directories for new files. |
| **Plan** | A structured markdown file (`PLAN-YYYY-NNN.md`) in `/Plans/` describing a multi-step task. |
| **Reconciliation** | Startup process that finds and resumes incomplete plans from previous sessions. |
| **Triage** | The process of classifying incoming tasks as simple or complex and routing them. |
| **Sidecar** | A companion `.md` file generated for non-markdown files moved to the vault. |
| **Dashboard** | `Dashboard.md` — auto-generated status overview of the vault. |
| **Inbox** | `/Inbox/` — entry point for new tasks. |
| **Needs Action** | `/Needs_Action/` — triaged simple tasks awaiting execution. |
| **Done** | `/Done/` — completed tasks. |
| **Pending Approval** | `/Pending_Approval/` — tasks awaiting human HITL approval. |
| **Approved** | `/Approved/` — human-approved actions. |
| **Rejected** | `/Rejected/` — human-rejected actions. |
| **SDD** | Spec-Driven Development — methodology used for feature planning and implementation. |
| **PHR** | Prompt History Record — log of AI interactions for traceability. |
| **ADR** | Architecture Decision Record — document capturing significant design decisions. |
