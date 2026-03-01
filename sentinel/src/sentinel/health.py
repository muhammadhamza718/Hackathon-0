"""Health check utilities for the sentinel watcher."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass
class HealthStatus:
    """Sentinel health check result."""
    healthy: bool
    watch_dir_exists: bool
    inbox_dir_exists: bool
    observer_running: bool
    uptime_seconds: float
    files_processed: int
    last_check: str


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
        healthy = watch_ok and inbox_ok and observer_running

        return HealthStatus(
            healthy=healthy,
            watch_dir_exists=watch_ok,
            inbox_dir_exists=inbox_ok,
            observer_running=observer_running,
            uptime_seconds=self.uptime,
            files_processed=self._files_processed,
            last_check=now,
        )
