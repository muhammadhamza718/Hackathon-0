"""Unit tests for sentinel.health module."""

from __future__ import annotations

from pathlib import Path

import pytest

from sentinel.health import HealthChecker


@pytest.fixture
def checker(tmp_path: Path) -> HealthChecker:
    watch = tmp_path / "watch"
    inbox = tmp_path / "inbox"
    watch.mkdir()
    inbox.mkdir()
    return HealthChecker(watch, inbox)


class TestHealthChecker:
    def test_healthy_when_all_ok(self, checker: HealthChecker):
        status = checker.check(observer_running=True)
        assert status.healthy is True

    def test_unhealthy_when_observer_stopped(self, checker: HealthChecker):
        status = checker.check(observer_running=False)
        assert status.healthy is False

    def test_unhealthy_missing_watch_dir(self, tmp_path: Path):
        c = HealthChecker(tmp_path / "nope", tmp_path)
        status = c.check(observer_running=True)
        assert status.healthy is False
        assert status.watch_dir_exists is False

    def test_uptime_positive(self, checker: HealthChecker):
        status = checker.check(observer_running=True)
        assert status.uptime_seconds >= 0

    def test_files_processed_default_zero(self, checker: HealthChecker):
        status = checker.check(observer_running=True)
        assert status.files_processed == 0

    def test_increment_processed(self, checker: HealthChecker):
        checker.increment_processed()
        checker.increment_processed()
        status = checker.check(observer_running=True)
        assert status.files_processed == 2

    def test_last_check_not_empty(self, checker: HealthChecker):
        status = checker.check(observer_running=True)
        assert len(status.last_check) > 0
