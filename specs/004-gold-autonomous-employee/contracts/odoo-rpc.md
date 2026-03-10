# Contract: Odoo 19+ JSON-RPC Integration

**Skill**: `odoo-accounting`
**Module**: `agents/gold/odoo_rpc_client.py`

## Interface

### `OdooRPCClient`

#### `__init__(config: OdooConfig)`
- **Precondition**: `ODOO_URL`, `ODOO_DB`, `ODOO_USERNAME`, `ODOO_API_KEY` available from env.
- **Postcondition**: Client initialized but NOT authenticated.

#### `authenticate() -> OdooSession`
- **Behavior**: Call `common` service `authenticate` method via JSON-RPC.
- **Returns**: `OdooSession` with authenticated `uid`.
- **Errors**: `AuthenticationError` if credentials invalid (401/403 → quarantine, no retry).
- **Side effects**: Logs `odoo_read` audit entry.

#### `search_read(model: str, domain: list, fields: list, limit: int = 100) -> list[dict]`
- **Behavior**: Autonomous READ operation. Calls `execute_kw` with `search_read`.
- **Precondition**: Authenticated session.
- **Returns**: List of record dicts.
- **Resilience**: Wrapped in `ResilientExecutor` — exponential backoff on 429/5xx.

#### `read(model: str, ids: list[int], fields: list) -> list[dict]`
- **Behavior**: Autonomous READ operation. Calls `execute_kw` with `read`.
- **Precondition**: Authenticated session.

#### `draft_create(model: str, values: dict) -> OdooOperation`
- **Behavior**: WRITE operation — does NOT execute. Creates an `OdooOperation` and writes it to `/Pending_Approval/` as a draft file.
- **Returns**: `OdooOperation` with `status=pending`, `requires_approval=True`.
- **Postcondition**: Draft file in `/Pending_Approval/` with full JSON-RPC payload.
- **Side effects**: Logs `odoo_write_draft` audit entry.

#### `draft_write(model: str, ids: list[int], values: dict) -> OdooOperation`
- **Behavior**: Same as `draft_create` but for update operations.

#### `execute_approved(operation: OdooOperation) -> OdooOperation`
- **Behavior**: Execute a previously approved write operation.
- **Precondition**: Corresponding file MUST exist in `/Approved/`.
- **Postcondition**: Operation executed against Odoo, result stored, file moved to `/Done/`.
- **Side effects**: Logs audit entry with full JSON-RPC payload.
- **Errors**: `ApprovalNotFoundError` if file not in `/Approved/`.

### `OdooConfig`

```python
@dataclass(frozen=True)
class OdooConfig:
    url: str           # ODOO_URL
    database: str      # ODOO_DB
    username: str      # ODOO_USERNAME
    api_key: str       # ODOO_API_KEY (NEVER logged or persisted)
```

## Data Mapping: Vault → Odoo

### Fetch Invoices (READ — autonomous)
```
Model: account.move
Domain: [('move_type', '=', 'out_invoice'), ('state', '=', 'posted')]
Fields: ['name', 'partner_id', 'amount_total', 'amount_residual', 'date', 'state']
```

### Fetch Revenue MTD (READ — autonomous, for CEO Briefing)
```
Model: account.move
Domain: [('move_type', '=', 'out_invoice'), ('state', '=', 'posted'),
         ('date', '>=', first_day_of_month), ('date', '<=', today)]
Fields: ['amount_total']
→ Sum amount_total for MTD revenue
```

### Create Invoice (WRITE — approval required)
```
Model: account.move
Method: create
Values: {
  'move_type': 'out_invoice',
  'partner_id': <int>,
  'invoice_line_ids': [(0, 0, {'name': <str>, 'quantity': <float>, 'price_unit': <float>})]
}
→ Draft to /Pending_Approval/
```

### Post Journal Entry (WRITE — approval required)
```
Model: account.move
Method: action_post
Args: [[<move_id>]]
→ Draft to /Pending_Approval/ (always, per Constitution XI)
```

## Success Metrics
- **SC-ODOO-1**: READ operations return valid data within 5 seconds.
- **SC-ODOO-2**: WRITE operations ALWAYS go to `/Pending_Approval/` — zero direct writes.
- **SC-ODOO-3**: API credentials never appear in vault files or audit logs.
- **SC-ODOO-4**: Transient errors trigger exponential backoff; logic errors trigger quarantine.
- **SC-ODOO-5**: Every Odoo call is logged with full JSON-RPC payload in audit trail.