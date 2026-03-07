"""Progress tracking for autonomous loop execution.

Provides detailed progress tracking, reporting, and visualization
for the Ralph Wiggum autonomous loop.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ProgressSnapshot:
    """A snapshot of loop progress at a point in time."""

    timestamp: str
    iteration: int
    active_plan_id: str | None = None
    active_step_index: int | None = None
    tasks_completed: int = 0
    tasks_failed: int = 0
    plans_completed: int = 0
    plans_blocked: int = 0
    idle_iterations: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "timestamp": self.timestamp,
            "iteration": self.iteration,
            "active_plan_id": self.active_plan_id,
            "active_step_index": self.active_step_index,
            "tasks_completed": self.tasks_completed,
            "tasks_failed": self.tasks_failed,
            "plans_completed": self.plans_completed,
            "plans_blocked": self.plans_blocked,
            "idle_iterations": self.idle_iterations,
        }


@dataclass
class ProgressReport:
    """Progress report for a time period."""

    period_start: str
    period_end: str
    total_iterations: int
    successful_iterations: int
    failed_iterations: int
    idle_iterations: int
    tasks_completed: int
    plans_completed: int
    plans_blocked: int
    average_iteration_time_ms: float = 0.0
    success_rate_pct: float = 0.0
    bottlenecks: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)

    def __post_init__(self):
        if self.total_iterations > 0:
            self.success_rate_pct = (
                self.successful_iterations / self.total_iterations
            ) * 100

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "period_start": self.period_start,
            "period_end": self.period_end,
            "total_iterations": self.total_iterations,
            "successful_iterations": self.successful_iterations,
            "failed_iterations": self.failed_iterations,
            "idle_iterations": self.idle_iterations,
            "tasks_completed": self.tasks_completed,
            "plans_completed": self.plans_completed,
            "plans_blocked": self.plans_blocked,
            "average_iteration_time_ms": self.average_iteration_time_ms,
            "success_rate_pct": round(self.success_rate_pct, 2),
            "bottlenecks": self.bottlenecks,
            "recommendations": self.recommendations,
        }


class ProgressTracker:
    """Tracks progress of autonomous loop execution.

    Features:
    - Real-time progress snapshots
    - Historical progress tracking
    - Progress reporting
    - Bottleneck detection
    """

    def __init__(self, logs_dir: str = "Logs"):
        """Initialize the progress tracker.

        Args:
            logs_dir: Directory for storing progress logs.
        """
        self.logs_dir = Path(logs_dir)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self._snapshots: list[ProgressSnapshot] = []
        self._iteration_times: list[float] = []
        self._current_iteration_start: datetime | None = None

    def start_iteration(self) -> None:
        """Mark the start of an iteration."""
        self._current_iteration_start = datetime.now(timezone.utc)

    def end_iteration(
        self,
        iteration: int,
        tasks_completed: int = 0,
        tasks_failed: int = 0,
        plans_completed: int = 0,
        plans_blocked: int = 0,
        active_plan_id: str | None = None,
        active_step_index: int | None = None,
        was_idle: bool = False,
    ) -> None:
        """Mark the end of an iteration.

        Args:
            iteration: Iteration number.
            tasks_completed: Tasks completed in this iteration.
            tasks_failed: Tasks failed in this iteration.
            plans_completed: Plans completed in this iteration.
            plans_blocked: Plans blocked in this iteration.
            active_plan_id: Currently active plan ID.
            active_step_index: Currently active step index.
            was_idle: Whether this was an idle iteration.
        """
        # Calculate iteration time
        iteration_time_ms = 0.0
        if self._current_iteration_start:
            iteration_time_ms = (
                datetime.now(timezone.utc) - self._current_iteration_start
            ).total_seconds() * 1000
            self._iteration_times.append(iteration_time_ms)

        # Create snapshot
        snapshot = ProgressSnapshot(
            timestamp=datetime.now(timezone.utc).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            ),
            iteration=iteration,
            active_plan_id=active_plan_id,
            active_step_index=active_step_index,
            tasks_completed=tasks_completed,
            tasks_failed=tasks_failed,
            plans_completed=plans_completed,
            plans_blocked=plans_blocked,
            idle_iterations=1 if was_idle else 0,
        )

        self._snapshots.append(snapshot)
        logger.debug(f"Progress snapshot at iteration {iteration}")

    def get_current_progress(self) -> dict[str, Any]:
        """Get current progress summary.

        Returns:
            Dictionary with current progress.
        """
        if not self._snapshots:
            return {
                "iteration": 0,
                "tasks_completed": 0,
                "plans_completed": 0,
                "success_rate": 0.0,
            }

        latest = self._snapshots[-1]
        total_tasks = sum(s.tasks_completed + s.tasks_failed for s in self._snapshots)
        total_plans = sum(s.plans_completed + s.plans_blocked for s in self._snapshots)

        return {
            "iteration": latest.iteration,
            "timestamp": latest.timestamp,
            "tasks_completed": sum(s.tasks_completed for s in self._snapshots),
            "tasks_failed": sum(s.tasks_failed for s in self._snapshots),
            "plans_completed": sum(s.plans_completed for s in self._snapshots),
            "plans_blocked": sum(s.plans_blocked for s in self._snapshots),
            "idle_iterations": sum(s.idle_iterations for s in self._snapshots),
            "success_rate": (
                (sum(s.tasks_completed for s in self._snapshots) / total_tasks * 100)
                if total_tasks > 0
                else 0.0
            ),
            "average_iteration_time_ms": (
                sum(self._iteration_times) / len(self._iteration_times)
                if self._iteration_times
                else 0.0
            ),
        }

    def generate_report(
        self, hours: float = 1.0
    ) -> ProgressReport:
        """Generate a progress report for a time period.

        Args:
            hours: Number of hours to include in the report.

        Returns:
            Progress report.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        cutoff_str = cutoff.strftime("%Y-%m-%dT%H:%M:%SZ")

        # Filter snapshots
        filtered = [
            s for s in self._snapshots
            if s.timestamp >= cutoff_str
        ]

        if not filtered:
            return ProgressReport(
                period_start=cutoff_str,
                period_end=datetime.now(timezone.utc).strftime(
                    "%Y-%m-%dT%H:%M:%SZ"
                ),
                total_iterations=0,
                successful_iterations=0,
                failed_iterations=0,
                idle_iterations=0,
                tasks_completed=0,
                plans_completed=0,
                plans_blocked=0,
            )

        # Calculate metrics
        total_iterations = len(filtered)
        successful = sum(
            1 for s in filtered
            if s.tasks_completed > 0 or s.plans_completed > 0
        )
        failed = sum(1 for s in filtered if s.tasks_failed > 0)
        idle = sum(s.idle_iterations for s in filtered)

        # Detect bottlenecks
        bottlenecks = self._detect_bottlenecks(filtered)

        # Generate recommendations
        recommendations = self._generate_recommendations(
            successful, failed, idle, total_iterations
        )

        return ProgressReport(
            period_start=filtered[0].timestamp,
            period_end=filtered[-1].timestamp,
            total_iterations=total_iterations,
            successful_iterations=successful,
            failed_iterations=failed,
            idle_iterations=idle,
            tasks_completed=sum(s.tasks_completed for s in filtered),
            plans_completed=sum(s.plans_completed for s in filtered),
            plans_blocked=sum(s.plans_blocked for s in filtered),
            average_iteration_time_ms=(
                sum(self._iteration_times[-total_iterations:]) / total_iterations
                if self._iteration_times
                else 0.0
            ),
            bottlenecks=bottlenecks,
            recommendations=recommendations,
        )

    def _detect_bottlenecks(
        self, snapshots: list[ProgressSnapshot]
    ) -> list[str]:
        """Detect bottlenecks from snapshots.

        Args:
            snapshots: List of progress snapshots.

        Returns:
            List of detected bottlenecks.
        """
        bottlenecks = []

        # Check for high idle rate
        idle_count = sum(s.idle_iterations for s in snapshots)
        if len(snapshots) > 0 and idle_count / len(snapshots) > 0.5:
            bottlenecks.append("High idle rate - insufficient work in queue")

        # Check for repeated failures
        if len(snapshots) >= 3:
            recent_failures = sum(s.tasks_failed for s in snapshots[-3:])
            if recent_failures > 5:
                bottlenecks.append("Repeated task failures detected")

        # Check for blocked plans
        blocked = sum(s.plans_blocked for s in snapshots)
        if blocked > 3:
            bottlenecks.append(f"{blocked} plans blocked - review dependencies")

        return bottlenecks

    def _generate_recommendations(
        self,
        successful: int,
        failed: int,
        idle: int,
        total: int,
    ) -> list[str]:
        """Generate recommendations based on metrics.

        Args:
            successful: Successful iterations.
            failed: Failed iterations.
            idle: Idle iterations.
            total: Total iterations.

        Returns:
            List of recommendations.
        """
        recommendations = []

        if total == 0:
            return ["No iterations to analyze"]

        success_rate = successful / total

        if success_rate < 0.7:
            recommendations.append(
                "Success rate below 70% - review error handling and task definitions"
            )

        idle_rate = idle / total
        if idle_rate > 0.3:
            recommendations.append(
                f"Idle rate at {idle_rate:.1%} - consider adding more work sources"
            )

        if failed > successful:
            recommendations.append(
                "More failures than successes - investigate root causes"
            )

        if not recommendations:
            recommendations.append("System operating normally")

        return recommendations

    def export_progress(
        self, output_path: str | Path | None = None
    ) -> str:
        """Export progress data to JSON.

        Args:
            output_path: Optional output path.

        Returns:
            Path to exported file.
        """
        if output_path is None:
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            output_path = self.logs_dir / f"progress_{timestamp}.json"
        else:
            output_path = Path(output_path)

        output_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "exported_at": datetime.now(timezone.utc).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            ),
            "current_progress": self.get_current_progress(),
            "snapshots": [s.to_dict() for s in self._snapshots[-100:]],  # Last 100
            "report_1h": self.generate_report(hours=1.0).to_dict(),
            "report_24h": self.generate_report(hours=24.0).to_dict(),
        }

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        logger.info(f"Exported progress to {output_path}")
        return str(output_path)

    def clear(self) -> None:
        """Clear all progress data."""
        self._snapshots.clear()
        self._iteration_times.clear()
        logger.info("Progress data cleared")
