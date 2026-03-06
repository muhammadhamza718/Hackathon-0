"""Health check utilities for the sentinel watcher."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum, unique
from pathlib import Path


@unique
class HealthState(Enum):
    """Overall health classification."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass(frozen=True)
class HealthStatus:
    """Immutable sentinel health check result."""

    state: HealthState
    watch_dir_exists: bool
    inbox_dir_exists: bool
    observer_running: bool
    uptime_seconds: float
    files_processed: int
    last_check: str

    @property
    def healthy(self) -> bool:
        """Backwards-compatible boolean health check."""
        return self.state is HealthState.HEALTHY

    @property
    def issues(self) -> tuple[str, ...]:
        """List of current health issues."""
        problems: list[str] = []
        if not self.watch_dir_exists:
            problems.append("watch directory missing")
        if not self.inbox_dir_exists:
            problems.append("inbox directory missing")
        if not self.observer_running:
            problems.append("observer not running")
        return tuple(problems)


class HealthChecker:
    """Monitors sentinel watcher health."""

    def __init__(self, watch_dir: Path, inbox_dir: Path) -> None:
        self.watch_dir = watch_dir
        self.inbox_dir = inbox_dir
        self._start_time = datetime.now(timezone.utc)
        self._files_processed = 0

    def increment_processed(self) -> None:
        """Record a file as processed."""
        self._files_processed += 1

    @property
    def uptime(self) -> float:
        """Get uptime in seconds."""
        delta = datetime.now(timezone.utc) - self._start_time
        return delta.total_seconds()

    def check(self, observer_running: bool = False) -> HealthStatus:
        """Perform a health check.

        Args:
            observer_running: Whether the file observer is currently running.

        Returns:
            HealthStatus with current system state.
        """
        now = datetime.now(timezone.utc).isoformat()
        watch_ok = self.watch_dir.exists() and self.watch_dir.is_dir()
        inbox_ok = self.inbox_dir.exists() and self.inbox_dir.is_dir()

        if watch_ok and inbox_ok and observer_running:
            state = HealthState.HEALTHY
        elif watch_ok and inbox_ok:
            state = HealthState.DEGRADED
        else:
            state = HealthState.UNHEALTHY

        return HealthStatus(
            state=state,
            watch_dir_exists=watch_ok,
            inbox_dir_exists=inbox_ok,
            observer_running=observer_running,
            uptime_seconds=self.uptime,
            files_processed=self._files_processed,
            last_check=now,
        )
