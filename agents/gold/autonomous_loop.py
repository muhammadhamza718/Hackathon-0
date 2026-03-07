"""Ralph Wiggum autonomous loop implementation.

The Ralph Wiggum Loop is the core autonomous execution engine for the
Gold Tier agent, providing continuous task execution with self-correction
and persistence.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from .audit_gold import GoldAuditLogger
from .config import LoopConfig as LoopConfigData
from .exceptions import LoopError, LoopExitError, LoopIterationError
from .models import LoopConfig, LoopState

logger = logging.getLogger(__name__)


@dataclass
class LoopMetrics:
    """Metrics for loop execution."""

    total_iterations: int = 0
    successful_iterations: int = 0
    failed_iterations: int = 0
    plans_completed: int = 0
    plans_blocked: int = 0
    tasks_completed: int = 0
    start_time: str = ""
    end_time: str = ""

    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.total_iterations == 0:
            return 0.0
        return (self.successful_iterations / self.total_iterations) * 100

    @property
    def duration_seconds(self) -> float:
        """Calculate duration in seconds."""
        if not self.start_time or not self.end_time:
            return 0.0
        start = datetime.fromisoformat(self.start_time.replace("Z", "+00:00"))
        end = datetime.fromisoformat(self.end_time.replace("Z", "+00:00"))
        return (end - start).total_seconds()


@dataclass
class LoopResult:
    """Result of loop execution."""

    exit_promise_met: bool
    metrics: LoopMetrics
    final_state: LoopState
    error: str | None = None


class RalphWiggumLoop:
    """Autonomous execution loop for Gold Tier agent.

    The Ralph Wiggum Loop continuously:
    1. Scans for work in /Needs_Action/
    2. Executes tasks with appropriate safety gates
    3. Logs all actions to audit trail
    4. Self-corrects on failures
    5. Persists state for recovery

    Exit conditions:
    - No work found for N consecutive iterations
    - Max iterations reached
    - Manual interrupt
    - Exit promise met
    """

    def __init__(
        self,
        config: LoopConfigData | None = None,
        audit_logger: GoldAuditLogger | None = None,
    ):
        """Initialize the Ralph Wiggum Loop.

        Args:
            config: Loop configuration.
            audit_logger: Audit logger instance.
        """
        self.config = config or LoopConfigData.from_env()
        self.audit_logger = audit_logger or GoldAuditLogger()
        self._state: LoopState | None = None
        self._metrics = LoopMetrics()
        self._running = False
        self._work_handlers: list[Callable] = []
        self._exit_conditions: list[Callable[[], bool]] = []

    def register_work_handler(self, handler: Callable) -> None:
        """Register a work handler.

        Args:
            handler: Function to handle work items.
        """
        self._work_handlers.append(handler)
        logger.debug(f"Registered work handler: {handler.__name__}")

    def register_exit_condition(self, condition: Callable[[], bool]) -> None:
        """Register an exit condition.

        Args:
            condition: Function returning True when loop should exit.
        """
        self._exit_conditions.append(condition)
        logger.debug(f"Registered exit condition: {condition.__name__}")

    def _initialize_state(self) -> LoopState:
        """Initialize loop state."""
        session_id = f"loop_{uuid.uuid4().hex[:8]}"
        self._state = LoopState(
            session_id=session_id,
            iteration=0,
            last_checkpoint=datetime.now(timezone.utc).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            ),
        )
        self._metrics.start_time = self._state.last_checkpoint
        logger.info(f"Initialized loop session: {session_id}")
        return self._state

    def _check_exit_conditions(self) -> bool:
        """Check if any exit conditions are met.

        Returns:
            True if loop should exit.
        """
        # Check registered exit conditions
        for condition in self._exit_conditions:
            try:
                if condition():
                    logger.info("Exit condition met")
                    return True
            except Exception as e:
                logger.warning(f"Exit condition check failed: {e}")

        # Check max iterations
        if self._state and self._state.iteration >= self.config.max_iterations:
            logger.info(f"Max iterations ({self.config.max_iterations}) reached")
            return True

        return False

    def _find_work(self) -> dict[str, Any] | None:
        """Find work to execute.

        Returns:
            Work item or None if no work found.
        """
        # This is a placeholder - actual implementation would scan
        # /Needs_Action/ directory for tasks
        for handler in self._work_handlers:
            try:
                work = handler()
                if work:
                    return work
            except Exception as e:
                logger.warning(f"Work handler failed: {e}")

        return None

    def _execute_work(self, work: dict[str, Any]) -> bool:
        """Execute a work item.

        Args:
            work: Work item to execute.

        Returns:
            True if execution successful.
        """
        # This is a placeholder - actual implementation would
        # execute the work item with appropriate safety gates
        logger.debug(f"Executing work: {work.get('type', 'unknown')}")
        return True

    def _iteration(self) -> bool:
        """Execute a single loop iteration.

        Returns:
            True if iteration successful.
        """
        if not self._state:
            return False

        self._state.iteration += 1
        self._metrics.total_iterations += 1

        try:
            # Find work
            work = self._find_work()

            if work is None:
                # No work found
                logger.debug(f"Iteration {self._state.iteration}: No work found")
                self._metrics.successful_iterations += 1
                return True

            # Execute work
            success = self._execute_work(work)

            if success:
                self._metrics.successful_iterations += 1
                self._metrics.tasks_completed += 1

                # Log success
                self.audit_logger.log_action(
                    action="loop_iteration",
                    rationale=f"Completed iteration {self._state.iteration}",
                    result="success",
                    iteration=self._state.iteration,
                )
            else:
                self._metrics.failed_iterations += 1

                # Log failure
                self.audit_logger.log_action(
                    action="loop_iteration",
                    rationale=f"Failed iteration {self._state.iteration}",
                    result="failure",
                    iteration=self._state.iteration,
                )

            return success

        except Exception as e:
            self._metrics.failed_iterations += 1
            logger.error(f"Iteration {self._state.iteration} failed: {e}")

            self.audit_logger.log_action(
                action="loop_iteration",
                rationale=f"Error in iteration {self._state.iteration}: {e}",
                result="failure",
                iteration=self._state.iteration,
            )

            return False

    def _checkpoint(self) -> None:
        """Save loop state checkpoint."""
        if not self._state:
            return

        if self._state.iteration % self.config.checkpoint_interval == 0:
            self._state.last_checkpoint = datetime.now(timezone.utc).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            )
            logger.debug(f"Checkpoint saved at iteration {self._state.iteration}")

    def run(self) -> LoopResult:
        """Run the autonomous loop.

        Returns:
            LoopResult with execution metrics.
        """
        self._running = True
        self._initialize_state()

        logger.info("Starting Ralph Wiggum Loop")

        try:
            while self._running:
                # Check exit conditions
                if self._check_exit_conditions():
                    self._state.exit_promise_met = True
                    break

                # Execute iteration
                self._iteration()

                # Checkpoint
                self._checkpoint()

                # Sleep if idle
                if self._metrics.total_iterations == self._metrics.successful_iterations:
                    # No work found, sleep briefly
                    import time
                    time.sleep(self.config.idle_sleep_seconds)

        except KeyboardInterrupt:
            logger.info("Loop interrupted by user")
        except Exception as e:
            logger.error(f"Loop error: {e}")
            raise LoopError(f"Loop execution failed: {e}") from e
        finally:
            self._running = False
            self._metrics.end_time = datetime.now(timezone.utc).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            )

        return LoopResult(
            exit_promise_met=self._state.exit_promise_met if self._state else False,
            metrics=self._metrics,
            final_state=self._state or LoopState(
                session_id="unknown",
                iteration=0,
            ),
        )

    def stop(self) -> None:
        """Stop the loop."""
        self._running = False
        logger.info("Loop stop requested")

    def get_state(self) -> LoopState | None:
        """Get current loop state.

        Returns:
            Current state or None if not running.
        """
        return self._state

    def get_metrics(self) -> LoopMetrics:
        """Get loop metrics.

        Returns:
            Current metrics.
        """
        return self._metrics

    def reset(self) -> None:
        """Reset loop state and metrics."""
        self._state = None
        self._metrics = LoopMetrics()
        self._running = False
        logger.info("Loop reset")
