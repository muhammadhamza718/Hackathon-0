"""Unit tests for sentinel.health module."""

from __future__ import annotations

from pathlib import Path

import pytest

from sentinel.health import HealthChecker, HealthState, HealthStatus


@pytest.fixture
def dirs(tmp_path: Path) -> tuple[Path, Path]:
    watch = tmp_path / "watch"
    inbox = tmp_path / "inbox"
    watch.mkdir()
    inbox.mkdir()
    return watch, inbox


@pytest.fixture
def checker(dirs: tuple[Path, Path]) -> HealthChecker:
    return HealthChecker(*dirs)


class TestHealthState:
    """Verify HealthState enum."""

    def test_three_states(self):
        assert len(HealthState) == 3

    @pytest.mark.parametrize(
        "state,expected",
        [
            (HealthState.HEALTHY, "healthy"),
            (HealthState.DEGRADED, "degraded"),
            (HealthState.UNHEALTHY, "unhealthy"),
        ],
    )
    def test_values(self, state: HealthState, expected: str):
        assert state.value == expected


class TestHealthStatus:
    """Verify frozen HealthStatus and computed properties."""

    def test_healthy_backwards_compat(self):
        status = HealthStatus(
            state=HealthState.HEALTHY, watch_dir_exists=True,
            inbox_dir_exists=True, observer_running=True,
            uptime_seconds=10.0, files_processed=0, last_check="now",
        )
        assert status.healthy is True

    def test_issues_lists_all_problems(self):
        status = HealthStatus(
            state=HealthState.UNHEALTHY, watch_dir_exists=False,
            inbox_dir_exists=False, observer_running=False,
            uptime_seconds=0.0, files_processed=0, last_check="now",
        )
        assert len(status.issues) == 3

    def test_no_issues_when_healthy(self):
        status = HealthStatus(
            state=HealthState.HEALTHY, watch_dir_exists=True,
            inbox_dir_exists=True, observer_running=True,
            uptime_seconds=10.0, files_processed=5, last_check="now",
        )
        assert status.issues == ()

    def test_frozen(self):
        status = HealthStatus(
            state=HealthState.HEALTHY, watch_dir_exists=True,
            inbox_dir_exists=True, observer_running=True,
            uptime_seconds=0.0, files_processed=0, last_check="now",
        )
        with pytest.raises(AttributeError):
            status.state = HealthState.UNHEALTHY  # type: ignore[misc]


class TestHealthChecker:
    def test_healthy_when_all_ok(self, checker: HealthChecker):
        status = checker.check(observer_running=True)
        assert status.state is HealthState.HEALTHY

    def test_degraded_when_observer_stopped(self, checker: HealthChecker):
        status = checker.check(observer_running=False)
        assert status.state is HealthState.DEGRADED

    def test_unhealthy_missing_dirs(self, tmp_path: Path):
        c = HealthChecker(tmp_path / "nope", tmp_path / "gone")
        status = c.check(observer_running=True)
        assert status.state is HealthState.UNHEALTHY

    def test_uptime_positive(self, checker: HealthChecker):
        assert checker.check(observer_running=True).uptime_seconds >= 0

    def test_increment_processed(self, checker: HealthChecker):
        checker.increment_processed()
        checker.increment_processed()
        assert checker.check(observer_running=True).files_processed == 2

    def test_last_check_not_empty(self, checker: HealthChecker):
        assert len(checker.check(observer_running=True).last_check) > 0
