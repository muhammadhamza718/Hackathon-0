"""Ralph Wiggum Autonomous Loop — persistent execution engine for Gold Tier.

The loop iterates over incomplete Plans and Needs_Action items until the
*exit promise* is met: all plans are COMPLETE/CANCELLED **and**
``/Needs_Action/`` is empty.  State is checkpointed after every iteration
to ``/Logs/loop-state.json`` so the loop can resume after interruption.

Constitution X governs this module.
"""

from __future__ import annotations

import atexit
import json
import signal
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Callable

from agents.constants import (
    DONE_DIR,
    LOGS_DIR,
    LOOP_STATE_FILE,
    NEEDS_ACTION_DIR,
    PLANS_DIR,
    STATUS_ACTIVE,
    STATUS_COMPLETE,
    STATUS_CANCELLED,
    STEP_DONE_MARKER,
    STEP_PENDING_MARKER,
    TIER_GOLD,
)
from agents.exceptions import CheckpointError, StateCorruptionError
from agents.gold.audit_gold import append_gold_log
from agents.gold.config import (
    LOOP_CHECKPOINT_INTERVAL,
    LOOP_IDLE_SLEEP_SECONDS,
    MAX_LOOP_ITERATIONS,
)
from agents.gold.models import LoopConfig, LoopResult, LoopState
from agents.plan_parser import summarize_plan
from agents.reconciler import find_incomplete_plans
from agents.utils import ensure_dir, utcnow_iso


@dataclass
class LoopProgress:
    """Progress tracking for Ralph Wiggum loop iterations.

    Attributes:
        iteration: Current iteration number.
        total_iterations: Maximum iterations configured.
        steps_completed: Steps completed in current iteration.
        steps_total: Total steps to complete.
        progress_pct: Progress percentage.
        blocked_plans: List of blocked plan IDs.
        elapsed_seconds: Time elapsed since loop start.
        estimated_remaining: Estimated time remaining.
    """

    iteration: int = 0
    total_iterations: int = 1000
    steps_completed: int = 0
    steps_total: int = 0
    progress_pct: float = 0.0
    blocked_plans: list[str] = field(default_factory=list)
    elapsed_seconds: float = 0.0
    estimated_remaining: float = 0.0

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "iteration": self.iteration,
            "total_iterations": self.total_iterations,
            "steps_completed": self.steps_completed,
            "steps_total": self.steps_total,
            "progress_pct": round(self.progress_pct, 1),
            "blocked_plans": self.blocked_plans,
            "elapsed_seconds": round(self.elapsed_seconds, 1),
            "estimated_remaining": round(self.estimated_remaining, 1),
        }

    def render_text(self) -> str:
        """Render progress as text visualization.

        Returns:
            Text-based progress display.
        """
        bar_width = 30
        filled = int(bar_width * self.progress_pct / 100)
        bar = "█" * filled + "░" * (bar_width - filled)

        lines = [
            f"╔══════════════════════════════════════════════════════════╗",
            f"║  Ralph Wiggum Loop Progress                              ║",
            f"╠══════════════════════════════════════════════════════════╣",
            f"║  Iteration: {self.iteration}/{self.total_iterations:<45}║",
            f"║  [{bar}] {self.progress_pct:>5.1f}%        ║",
            f"║  Steps: {self.steps_completed}/{self.steps_total:<49}║",
        ]

        if self.blocked_plans:
            lines.append(f"║  Blocked: {len(self.blocked_plans)} plans                            ║")
            for plan in self.blocked_plans[:3]:
                lines.append(f"║    - {plan[:50]:<50}║")

        lines.extend([
            f"║  Elapsed: {self.elapsed_seconds:>6.1f}s                              ║",
            f"╚══════════════════════════════════════════════════════════╝",
        ])

        return "\n".join(lines)


class AutonomousLoop:
    """Non-terminating reasoning loop that persists until exit promise met.
    
    The loop iterates over incomplete Plans and Needs_Action items until
    the exit promise is met. State is checkpointed after every iteration
    to enable session resumption after interruption.
    
    Attributes:
        vault_root: Root path of the Obsidian vault.
        config: Loop configuration (max iterations, checkpoint interval, etc.).
        step_executor: Callable to execute individual plan steps.
    """

    def __init__(
        self,
        vault_root: Path,
        config: LoopConfig | None = None,
        step_executor: Callable[[Path, int], bool] | None = None,
    ) -> None:
        """Initialize the autonomous loop.
        
        Args:
            vault_root: Root path of the Obsidian vault.
            config: Optional loop configuration. Uses defaults if not provided.
            step_executor: Optional callable to execute individual plan steps.
                          Defaults to no-op executor.
        """
        self.vault_root = vault_root
        self.config = config or LoopConfig(
            max_iterations=MAX_LOOP_ITERATIONS,
            checkpoint_interval=LOOP_CHECKPOINT_INTERVAL,
            idle_sleep_seconds=LOOP_IDLE_SLEEP_SECONDS,
        )
        self._step_executor = step_executor or self._default_step_executor
        self._state: LoopState | None = None
        self._running = True

        # Register signal handlers for graceful checkpoint
        self._register_signals()

    # ------------------------------------------------------------------
    # Signal handling
    # ------------------------------------------------------------------

    def _register_signals(self) -> None:
        """Register atexit and signal handlers to checkpoint before exit."""
        atexit.register(self._on_exit)
        try:
            signal.signal(signal.SIGINT, self._signal_handler)
            signal.signal(signal.SIGTERM, self._signal_handler)
        except (OSError, ValueError):
            # signal registration can fail in non-main threads
            pass

    def _signal_handler(self, signum: int, frame: object) -> None:
        """Handle SIGINT/SIGTERM — checkpoint and stop."""
        self._running = False
        self.checkpoint()

    def _on_exit(self) -> None:
        """atexit handler — ensure state is checkpointed."""
        if self._state is not None:
            self.checkpoint()

    # ------------------------------------------------------------------
    # State persistence
    # ------------------------------------------------------------------

    def _state_path(self) -> Path:
        """Return path to ``/Logs/loop-state.json``."""
        return ensure_dir(self.vault_root / LOGS_DIR) / LOOP_STATE_FILE

    def checkpoint(self) -> None:
        """Persist current ``LoopState`` to disk.
        
        Raises:
            CheckpointError: If state cannot be persisted to disk.
        """
        if self._state is None:
            return
        ts = utcnow_iso()
        state_path = self._state_path()
        try:
            # Create updated state with new checkpoint timestamp
            self._state = LoopState(
                session_id=self._state.session_id,
                iteration=self._state.iteration,
                active_plan_id=self._state.active_plan_id,
                active_step_index=self._state.active_step_index,
                blocked_plans=self._state.blocked_plans,
                last_checkpoint=ts,
                exit_promise_met=self._state.exit_promise_met,
            )
            state_path.write_text(
                json.dumps(self._state.to_dict(), indent=2) + "\n",
                encoding="utf-8",
            )
        except (OSError, TypeError, ValueError) as exc:
            raise CheckpointError(
                f"Failed to checkpoint loop state: {exc}",
                state_path=str(state_path),
                original_exception=exc,
            ) from exc

    def resume(self) -> LoopState:
        """Load ``LoopState`` from disk if it exists.

        Returns:
            The restored state.
            
        Raises:
            StateCorruptionError: If state file is corrupted.
        """
        path = self._state_path()
        if not path.exists():
            return LoopState(session_id=str(uuid.uuid4())[:8])
        try:
            content = path.read_text(encoding="utf-8")
            data = json.loads(content)
            return LoopState.from_dict(data)
        except json.JSONDecodeError as exc:
            raise StateCorruptionError(
                state_path=str(path),
                corruption_type="invalid_json",
                recovery_suggestion="Delete corrupted state file to start fresh session",
            ) from exc
        except (KeyError, TypeError) as exc:
            raise StateCorruptionError(
                state_path=str(path),
                corruption_type="missing_fields",
                recovery_suggestion="Delete corrupted state file to start fresh session",
            ) from exc
        except OSError as exc:
            raise StateCorruptionError(
                state_path=str(path),
                corruption_type="read_error",
                recovery_suggestion="Check file permissions and disk space",
            ) from exc

    # ------------------------------------------------------------------
    # Exit promise
    # ------------------------------------------------------------------

    def is_exit_promise_met(self) -> bool:
        """All plans COMPLETE/CANCELLED **and** /Needs_Action/ empty."""
        plans_dir = self.vault_root / PLANS_DIR
        needs_action_dir = self.vault_root / NEEDS_ACTION_DIR

        # Check plans
        if plans_dir.exists():
            incomplete = find_incomplete_plans(self.vault_root)
            if incomplete:
                return False

        # Check Needs_Action
        if needs_action_dir.exists():
            items = [
                f for f in needs_action_dir.iterdir() if f.is_file()
            ]
            if items:
                return False

        return True

    # ------------------------------------------------------------------
    # Progress tracking
    # ------------------------------------------------------------------

    def get_progress(self, start_time: float, iteration: int) -> LoopProgress:
        """Get current loop progress.

        Args:
            start_time: Loop start time (monotonic).
            iteration: Current iteration number.

        Returns:
            LoopProgress with current status.
        """
        elapsed = time.monotonic() - start_time
        total_steps = self._count_total_steps()
        completed = self._count_completed_steps()

        progress_pct = (completed / total_steps * 100) if total_steps > 0 else 0

        # Estimate remaining time
        if completed > 0 and progress_pct > 0:
            total_estimated = elapsed / (progress_pct / 100)
            remaining = total_estimated - elapsed
        else:
            remaining = 0

        return LoopProgress(
            iteration=iteration,
            total_iterations=self.config.max_iterations,
            steps_completed=completed,
            steps_total=total_steps,
            progress_pct=progress_pct,
            blocked_plans=list(self._state.blocked_plans) if self._state else [],
            elapsed_seconds=elapsed,
            estimated_remaining=remaining,
        )

    def _count_total_steps(self) -> int:
        """Count total steps across all incomplete plans.

        Returns:
            Total step count.
        """
        total = 0
        plans_dir = self.vault_root / PLANS_DIR
        if not plans_dir.exists():
            return 0

        for plan_file in plans_dir.iterdir():
            if plan_file.is_file():
                content = plan_file.read_text(encoding="utf-8")
                # Count step markers
                total += content.count("- [ ]")  # Pending steps
                total += content.count("- [x]")  # Completed steps

        return total

    def _count_completed_steps(self) -> int:
        """Count completed steps.

        Returns:
            Completed step count.
        """
        completed = 0
        plans_dir = self.vault_root / PLANS_DIR
        if not plans_dir.exists():
            return 0

        for plan_file in plans_dir.iterdir():
            if plan_file.is_file():
                content = plan_file.read_text(encoding="utf-8")
                completed += content.count("- [x]")

        return completed

    def render_state_diagram(self) -> str:
        """Render current loop state as text-based diagram.

        Returns:
            ASCII art state diagram.
        """
        if not self._state:
            return "No active state"

        lines = [
            "╔══════════════════════════════════════════════════════════╗",
            "║              Ralph Wiggum Loop State                     ║",
            "╠══════════════════════════════════════════════════════════╣",
            f"║  Session: {self._state.session_id:<46}║",
            f"║  Iteration: {self._state.iteration:<45}║",
            "╠══════════════════════════════════════════════════════════╣",
        ]

        # Current task
        if self._state.active_plan_id:
            lines.append(f"║  Current Plan: {self._state.active_plan_id:<40}║")
            if self._state.active_step_index is not None:
                lines.append(f"║  Current Step: {self._state.active_step_index:<40}║")
        else:
            lines.append("║  Current Plan: (none)                                   ║")

        lines.append("╠══════════════════════════════════════════════════════════╣")

        # Blocked plans
        if self._state.blocked_plans:
            lines.append(f"║  Blocked Plans: {len(self._state.blocked_plans):<41}║")
            for plan in self._state.blocked_plans[:5]:
                display = plan[:45]
                lines.append(f"║    🚫 {display:<48}║")
        else:
            lines.append("║  Blocked Plans: (none)                                  ║")

        lines.append("╠══════════════════════════════════════════════════════════╣")

        # Exit promise status
        status = "✅ MET" if self._state.exit_promise_met else "⏳ PENDING"
        lines.append(f"║  Exit Promise: {status:<41}║")
        lines.append("╚══════════════════════════════════════════════════════════╝")

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Smart backoff for blocked tasks
    # ------------------------------------------------------------------

    def _check_blocked_plan(self, plan_id: str) -> bool:
        """Check if a plan is still blocked (HITL pending).

        Args:
            plan_id: Plan ID to check.

        Returns:
            True if still blocked.
        """
        # Check if plan has been approved/moved
        plans_dir = self.vault_root / PLANS_DIR
        approved_dir = self.vault_root / "Approved"

        plan_file = plans_dir / f"{plan_id}.md"
        approved_file = approved_dir / f"{plan_id}.md"

        # If plan moved to Approved, no longer blocked
        if approved_file.exists():
            return False

        # If plan still in Plans with pending status, still blocked
        if plan_file.exists():
            content = plan_file.read_text(encoding="utf-8")
            if "status: pending_approval" in content.lower():
                return True

        return False

    def _get_backoff_delay(self, consecutive_checks: int) -> float:
        """Calculate exponential backoff delay for blocked plan checks.

        Args:
            consecutive_checks: Number of consecutive checks.

        Returns:
            Delay in seconds (max 300s / 5 minutes).
        """
        # Exponential backoff: 1s, 2s, 4s, 8s, 16s, 32s, 64s, 128s, 256s, 300s...
        delay = min(2 ** consecutive_checks, 300)
        return delay

    def _process_blocked_plans(self) -> list[str]:
        """Process blocked plans with smart backoff.

        Returns:
            List of plan IDs that are still blocked.
        """
        if not self._state:
            return []

        still_blocked: list[str] = []
        newly_unblocked: list[str] = []

        for plan_id in self._state.blocked_plans:
            if self._check_blocked_plan(plan_id):
                still_blocked.append(plan_id)
            else:
                newly_unblocked.append(plan_id)

        # Log newly unblocked plans
        for plan_id in newly_unblocked:
            append_gold_log(
                self.vault_root,
                action="plan_unblocked",
                details=f"Plan {plan_id} is no longer blocked",
                rationale="HITL approval received or plan status changed",
            )

        return still_blocked

    # ------------------------------------------------------------------
    # Default step executor
    # ------------------------------------------------------------------

    @staticmethod
    def _default_step_executor(plan_path: Path, step_index: int) -> bool:
        """Default no-op step executor — returns True (step completed).

        In production, this is replaced with actual task execution logic.
        """
        return True

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------

    def run(self) -> LoopResult:
        """Execute the Ralph Wiggum loop until exit promise or max iterations.

        Returns:
            ``LoopResult`` summarizing the session.
        """
        start_time = time.monotonic()

        # Resume or initialize
        restored = self.resume()
        if restored is not None:
            self._state = restored
        else:
            self._state = LoopState(
                session_id=str(uuid.uuid4())[:8],
            )

        plans_completed = 0
        plans_blocked = 0
        tasks_completed = 0
        iteration = self._state.iteration

        while self._running and iteration < self.config.max_iterations:
            # Check exit promise
            if self.is_exit_promise_met():
                self._state = LoopState(
                    session_id=self._state.session_id,
                    iteration=iteration,
                    exit_promise_met=True,
                    last_checkpoint=utcnow_iso(),
                )
                self.checkpoint()
                break

            # Scan for work
            plans_dir = self.vault_root / PLANS_DIR
            needs_action_dir = self.vault_root / NEEDS_ACTION_DIR

            did_work = False

            # 1. Process incomplete plans
            if plans_dir.exists():
                incomplete = find_incomplete_plans(self.vault_root)
                for plan_path in incomplete:
                    if not self._running:
                        break
                    plan_id = plan_path.stem

                    # Skip blocked plans
                    if plan_id in self._state.blocked_plans:
                        plans_blocked += 1
                        continue

                    # Try to execute next step
                    content = plan_path.read_text(encoding="utf-8")
                    summary = summarize_plan(content)
                    step_idx = 0
                    for i, step in enumerate(summary.steps):
                        if not step.get("checked", False):
                            step_idx = i
                            break

                    # Update state
                    self._state = LoopState(
                        session_id=self._state.session_id,
                        iteration=iteration,
                        active_plan_id=plan_id,
                        active_step_index=step_idx,
                        blocked_plans=self._state.blocked_plans,
                        last_checkpoint=self._state.last_checkpoint,
                    )

                    step_start = time.monotonic()
                    success = self._step_executor(plan_path, step_idx)
                    duration_ms = int((time.monotonic() - step_start) * 1000)

                    if success:
                        tasks_completed += 1
                        did_work = True

                    # Log iteration
                    append_gold_log(
                        self.vault_root,
                        action="complete" if success else "error",
                        source_file=str(plan_path.relative_to(self.vault_root)),
                        details=f"Step {step_idx} of {plan_id}",
                        result="success" if success else "failure",
                        rationale=f"{plan_id}#Step-{step_idx}",
                        iteration=iteration,
                        duration_ms=duration_ms,
                    )

            # 2. Process /Needs_Action/ items
            if needs_action_dir.exists():
                for item in sorted(needs_action_dir.iterdir()):
                    if not item.is_file():
                        continue
                    if not self._running:
                        break
                    # Move completed items to Done
                    done_dir = ensure_dir(self.vault_root / DONE_DIR)
                    item.rename(done_dir / item.name)
                    tasks_completed += 1
                    did_work = True

            iteration += 1

            # Checkpoint
            if iteration % self.config.checkpoint_interval == 0:
                self._state = LoopState(
                    session_id=self._state.session_id,
                    iteration=iteration,
                    blocked_plans=self._state.blocked_plans,
                    last_checkpoint=utcnow_iso(),
                )
                self.checkpoint()

            # Idle sleep if no work found
            if not did_work:
                time.sleep(self.config.idle_sleep_seconds)

        elapsed = time.monotonic() - start_time
        exit_met = self.is_exit_promise_met()

        return LoopResult(
            exit_promise_met=exit_met,
            total_iterations=iteration,
            plans_completed=plans_completed,
            plans_blocked=plans_blocked,
            tasks_completed=tasks_completed,
            duration_seconds=elapsed,
        )
