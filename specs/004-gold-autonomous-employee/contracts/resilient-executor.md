# Contract: Resilient Executor & Error Handling

**Skill**: `resilient-operations`
**Module**: `agents/gold/resilient_executor.py`

## Interface

### `ResilientExecutor`

#### `__init__(vault_root: Path, audit_logger: GoldAuditLogger)`
- **Postcondition**: Executor initialized with empty circuit breaker states.

#### `execute(operation: Callable[..., T], api_name: str, *args, **kwargs) -> T`
- **Behavior**: Execute an operation with full resilience stack.
- **Flow**:
  1. Check circuit breaker for `api_name`. If open → raise `CircuitOpenError`.
  2. Try operation.
  3. On success → reset circuit breaker, return result.
  4. On transient error (429, 5xx, timeout) → exponential backoff, retry up to 5 times.
  5. On logic error (400, 401, 403, 422) → NO retry, quarantine immediately.
  6. After 5 failed retries → mark operation as failed, increment circuit breaker.
  7. At 3 consecutive failures → open circuit breaker.
- **Side effects**: Logs `retry` entries on each attempt, `quarantine` on logic errors, `circuit_breaker` on breaker open.

#### `classify_error(error: Exception) -> ErrorType`
- **Returns**: `ErrorType.TRANSIENT` or `ErrorType.LOGIC`.
- **Classification**:
  - `TransientError`: HTTP 429, 500, 502, 503, 504, `ConnectionError`, `TimeoutError`.
  - `LogicError`: HTTP 400, 401, 403, 422, `ValueError`, `ValidationError`.

#### `quarantine(filename: str, error: Exception, payload: dict) -> QuarantinedItem`
- **Behavior**: Move file to `/Needs_Action/` with `[QUARANTINED]_` prefix. Create P0 alert.
- **Postcondition**: File renamed, P0 alert created in `/Needs_Action/`, audit entry logged.

#### `get_circuit_state(api_name: str) -> CircuitBreakerState`
- **Returns**: Current circuit breaker state for the given API.

### Backoff Sequence

```
Attempt 1: immediate
Attempt 2: 1s  + jitter(0, 0.5s)
Attempt 3: 2s  + jitter(0, 1.0s)
Attempt 4: 4s  + jitter(0, 2.0s)
Attempt 5: 8s  + jitter(0, 4.0s)
Attempt 6: 16s + jitter(0, 8.0s)  [if max_retries > 5]
Cap: 60s maximum delay
```

Jitter uses uniform random distribution to prevent thundering herd.

### `ErrorType`

```python
class ErrorType(Enum):
    TRANSIENT = "transient"  # Retry with backoff
    LOGIC = "logic"          # Quarantine immediately
```

### Quarantine Alert Format (P0 in /Needs_Action/)

Filename: `[QUARANTINED]_<original-filename>.md`

```markdown
---
priority: P0
type: system-failure
quarantined_at: 2026-03-05T14:30:00Z
original_file: odoo-invoice-create.md
---

# System Failure Alert

**Error Type**: Logic Error (HTTP 422)
**API**: odoo
**Operation**: account.move.create

## Error Details
Unprocessable Entity: partner_id 999 does not exist.

## Original Payload
```json
{"model": "account.move", "method": "create", "values": {...}}
```

## Required Action
Review and fix the payload, then move this file to `/Needs_Action/` without the [QUARANTINED] prefix to retry.
```

## Success Metrics
- **SC-RESIL-1**: Transient errors retry with correct exponential backoff timing.
- **SC-RESIL-2**: Logic errors quarantine immediately — zero retries.
- **SC-RESIL-3**: Circuit breaker opens after 3 consecutive failures to same API.
- **SC-RESIL-4**: Quarantined items produce P0 alert in `/Needs_Action/`.
- **SC-RESIL-5**: Jitter prevents synchronized retries across concurrent operations.