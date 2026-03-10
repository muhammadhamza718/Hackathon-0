# Contract: Ralph Wiggum Autonomous Loop

**Skill**: `gold-autonomous-loop`
**Module**: `agents/gold/autonomous_loop.py`

## Interface

### `AutonomousLoop`

#### `__init__(vault_root: Path, config: LoopConfig)`
- **Precondition**: `vault_root` exists and contains required vault folders.
- **Postcondition**: Loop state initialized (fresh or resumed from checkpoint).

#### `run() -> LoopResult`
- **Behavior**: Non-terminating loop that iterates until exit promise is met.
- **Cycle**:
  1. Scan `/Plans/` for incomplete plans (unchecked roadmap items).
  2. Scan `/Needs_Action/` for unresolved tasks.
  3. If items remain: execute next step, log progress, checkpoint, repeat.
  4. If ALL items resolved: return `LoopResult(exit_promise_met=True)`.
- **HITL handling**: If current step requires approval, add plan to `blocked_plans`, skip to next non-blocked task.
- **Postcondition**: Every iteration is logged via `GoldAuditEntry` with `iteration` count.
- **Side effects**: Writes to `/Logs/loop-state.json`, `/Logs/YYYY-MM-DD.json`, updates `/Plans/`.

#### `checkpoint() -> None`
- **Behavior**: Persist current `LoopState` to `/Logs/loop-state.json`.
- **When called**: After every iteration, and on signal interception (SIGINT/SIGTERM/atexit).
- **Postcondition**: `loop-state.json` reflects current position.

#### `resume() -> LoopState | None`
- **Behavior**: Load `LoopState` from `/Logs/loop-state.json` if it exists.
- **Returns**: `LoopState` if resuming, `None` if fresh start.

#### `is_exit_promise_met() -> bool`
- **Behavior**: Returns True when:
  - All plans in `/Plans/` have status COMPLETE or CANCELLED.
  - `/Needs_Action/` contains zero unresolved files.

### `LoopConfig`

```python
@dataclass(frozen=True)
class LoopConfig:
    max_iterations: int = 1000  # Safety cap to prevent infinite loops
    checkpoint_interval: int = 1  # Checkpoint every N iterations
    idle_sleep_seconds: float = 5.0  # Sleep between iterations when no work
```

### `LoopResult`

```python
@dataclass(frozen=True)
class LoopResult:
    exit_promise_met: bool
    total_iterations: int
    plans_completed: int
    plans_blocked: int
    tasks_completed: int
    duration_seconds: float
```

## Success Metrics
- **SC-LOOP-1**: Loop resumes correctly from checkpoint after process kill (SIGTERM).
- **SC-LOOP-2**: HITL-blocked tasks do not stall the loop; non-blocked tasks continue.
- **SC-LOOP-3**: Exit promise evaluates correctly when all work is done.
- **SC-LOOP-4**: `max_iterations` safety cap prevents infinite loops.
- **SC-LOOP-5**: Every iteration produces a `GoldAuditEntry` with correct `iteration` count.