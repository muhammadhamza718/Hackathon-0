# Quickstart: Gold Tier Autonomous Employee

## Prerequisites

- Python 3.11+ with `pip`
- Existing vault structure (Bronze Tier initialized)
- Silver Tier reasoning modules (`plan_manager`, `reconciler`, `hitl_gate`)
- Self-hosted Odoo Community 19+ instance (for accounting features)
- Browser MCP server running locally (for social media features)

## 1. Environment Setup

Copy and configure the environment file:

```bash
cp .env.example .env
# Edit .env with your Odoo credentials and MCP config
```

Required variables for Gold Tier:

```env
ODOO_URL=http://localhost:8069
ODOO_DB=my_company
ODOO_USERNAME=admin
ODOO_API_KEY=your-odoo-api-key
BROWSER_MCP_HOST=localhost
BROWSER_MCP_PORT=3000
PAYMENT_APPROVAL_THRESHOLD=100.00
CEO_BRIEFING_DAY=6
CEO_BRIEFING_HOUR=22
```

## 2. Verify Vault Structure

The Gold Tier requires these vault directories (create if missing):

```
vault/
├── Inbox/
├── Needs_Action/
├── Pending_Approval/
├── Approved/
├── Rejected/
├── Done/
├── Plans/
├── Logs/
├── Dashboard.md
└── Company_Handbook.md
```

## 3. Verify Odoo Connection

```bash
python -m agents.gold.odoo_rpc_client --test-connection
```

Expected: `Connected to Odoo 19.0 as uid=2 on database my_company`

## 4. Run the Gold Tier Agent

The Gold Tier agent is invoked via the `gold-tier-autonomous` Claude agent definition:

```
claude --agent gold-tier-autonomous
```

On startup, the agent will:
1. **Reconcile** — Scan `/Plans/` for incomplete plans, resume from checkpoint.
2. **Assess** — Read tasks from `/Needs_Action/`.
3. **Loop** — Execute the Ralph Wiggum loop until exit promise is met.

## 5. Test the Approval Workflow

Place a test task requiring approval in `/Needs_Action/`:

```markdown
---
priority: P2
type: payment
amount: 150.00
---
# Test Payment Task
Pay vendor $150 for consulting services.
```

The agent will:
1. Detect `amount > $100` → route to `/Pending_Approval/`.
2. Wait for human to move file to `/Approved/`.
3. Execute the payment via Odoo after approval.

## 6. Trigger a CEO Briefing (Manual Test)

Set `CEO_BRIEFING_HOUR` to current hour in `.env`, then run the agent. It will generate a briefing in `/Needs_Action/CEO-Briefing-YYYY-WNN.md`.

## 7. Module Map

| Feature | Skill | Entry Module |
|---|---|---|
| Autonomous Loop | `gold-autonomous-loop` | `agents/gold/autonomous_loop.py` |
| Odoo Accounting | `odoo-accounting` | `agents/gold/odoo_rpc_client.py` |
| Social Media | `social-media-management` | `agents/gold/social_bridge.py` |
| CEO Briefing | `ceo-briefing-engine` | `agents/gold/briefing_engine.py` |
| Resilience | `resilient-operations` | `agents/gold/resilient_executor.py` |
| Audit Logging | `gold-audit-trail` | `agents/gold/audit_gold.py` |
| Safety Gate | `gold-safety-gate` | `agents/gold/safety_gate.py` |

## 8. Running Tests

```bash
# Unit tests
pytest tests/unit/test_gold_*.py -v

# Integration tests (requires Odoo connection)
pytest tests/integration/test_gold_*.py -v

# Full test suite
make test
```