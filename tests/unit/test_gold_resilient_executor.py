"""Unit tests for agents.gold.resilient_executor module."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from agents.exceptions import (
    CircuitOpenError,
    LogicAPIError,
    TransientAPIError,
)
from agents.gold.models import CircuitBreakerState, ErrorType
from agents.gold.resilient_executor import (
    ResilientExecutor,
    _backoff_delay,
    classify_error,
)


class TestClassifyError:
    def test_transient_api_error(self):
        assert classify_error(TransientAPIError("timeout")) is ErrorType.TRANSIENT

    def test_connection_error(self):
        assert classify_error(ConnectionError("refused")) is ErrorType.TRANSIENT

    def test_timeout_error(self):
        assert classify_error(TimeoutError("expired")) is ErrorType.TRANSIENT

    def test_logic_api_error(self):
        assert classify_error(LogicAPIError("bad request")) is ErrorType.LOGIC

    def test_value_error(self):
        assert classify_error(ValueError("invalid")) is ErrorType.LOGIC

    def test_type_error(self):
        assert classify_error(TypeError("wrong type")) is ErrorType.LOGIC

    def test_unknown_defaults_transient(self):
        assert classify_error(RuntimeError("unknown")) is ErrorType.TRANSIENT


class TestBackoffDelay:
    def test_first_attempt_range(self):
        delay = _backoff_delay(0)
        assert 1.0 <= delay <= 1.5  # base=1, jitter up to 0.5

    def test_increases_with_attempt(self):
        d0 = _backoff_delay(0)
        d2 = _backoff_delay(2)
        # attempt 2 = min(1*4, 60) = 4, jitter [0, 2] → [4, 6]
        assert d2 > d0

    def test_capped_at_max(self):
        delay = _backoff_delay(100)
        assert delay <= 90.0  # 60 base + 30 max jitter


class TestCircuitBreakerState:
    def test_initial_state(self):
        cb = CircuitBreakerState(api_name="test")
        assert cb.consecutive_failures == 0
        assert cb.is_open is False

    def test_record_failure_increments(self):
        cb = CircuitBreakerState(api_name="test")
        cb.record_failure("err1")
        assert cb.consecutive_failures == 1
        assert cb.is_open is False

    def test_opens_at_threshold(self):
        cb = CircuitBreakerState(api_name="test")
        for i in range(3):
            cb.record_failure(f"err{i}")
        assert cb.is_open is True
        assert cb.opened_at is not None

    def test_success_resets(self):
        cb = CircuitBreakerState(api_name="test")
        cb.record_failure("err1")
        cb.record_failure("err2")
        cb.record_success()
        assert cb.consecutive_failures == 0
        assert cb.is_open is False


class TestResilientExecutor:
    @pytest.fixture
    def vault(self, tmp_path: Path) -> Path:
        (tmp_path / "Logs").mkdir()
        (tmp_path / "Needs_Action").mkdir()
        return tmp_path

    @pytest.fixture
    def executor(self, vault: Path) -> ResilientExecutor:
        return ResilientExecutor(vault)

    def test_success_returns_result(self, executor: ResilientExecutor):
        result = executor.execute(lambda: 42, "test_api")
        assert result == 42

    def test_success_resets_breaker(self, executor: ResilientExecutor):
        cb = executor.get_circuit_state("test_api")
        cb.record_failure("prior")
        executor.execute(lambda: "ok", "test_api")
        assert cb.consecutive_failures == 0

    @patch("agents.gold.resilient_executor.time.sleep")
    def test_retries_on_transient(self, mock_sleep, executor: ResilientExecutor):
        counter = {"n": 0}

        def flaky():
            counter["n"] += 1
            if counter["n"] < 3:
                raise TransientAPIError("timeout")
            return "success"

        result = executor.execute(flaky, "test_api", max_retries=5)
        assert result == "success"
        assert counter["n"] == 3

    def test_logic_error_no_retry(self, executor: ResilientExecutor):
        def bad():
            raise LogicAPIError("bad request", status_code=400)

        with pytest.raises(LogicAPIError):
            executor.execute(bad, "test_api", max_retries=5)

    @patch("agents.gold.resilient_executor.time.sleep")
    def test_exhausted_retries_raises(self, mock_sleep, executor: ResilientExecutor):
        def always_fail():
            raise TransientAPIError("timeout")

        with pytest.raises(TransientAPIError, match="retries exhausted"):
            executor.execute(always_fail, "test_api", max_retries=2)

    def test_circuit_open_raises(self, executor: ResilientExecutor):
        cb = executor.get_circuit_state("broken_api")
        cb.is_open = True
        with pytest.raises(CircuitOpenError, match="broken_api"):
            executor.execute(lambda: None, "broken_api")

    @patch("agents.gold.resilient_executor.time.sleep")
    def test_circuit_opens_after_threshold(
        self, mock_sleep, executor: ResilientExecutor
    ):
        def always_fail():
            raise TransientAPIError("fail")

        with pytest.raises((TransientAPIError, CircuitOpenError)):
            executor.execute(always_fail, "fragile_api", max_retries=5)

        cb = executor.get_circuit_state("fragile_api")
        assert cb.is_open is True


class TestQuarantine:
    @pytest.fixture
    def vault(self, tmp_path: Path) -> Path:
        (tmp_path / "Logs").mkdir()
        (tmp_path / "Needs_Action").mkdir()
        return tmp_path

    @pytest.fixture
    def executor(self, vault: Path) -> ResilientExecutor:
        return ResilientExecutor(vault)

    def test_creates_alert_file(self, executor: ResilientExecutor, vault: Path):
        item = executor.quarantine(
            "invoice-001.md", LogicAPIError("bad", status_code=400)
        )
        assert item.alert_created is True
        alert = vault / "Needs_Action" / item.quarantined_filename
        assert alert.exists()

    def test_quarantine_prefix(self, executor: ResilientExecutor):
        item = executor.quarantine("test.md", ValueError("invalid"))
        assert item.quarantined_filename.startswith("[QUARANTINED]_")

    def test_p0_priority_in_alert(self, executor: ResilientExecutor, vault: Path):
        item = executor.quarantine("test.md", RuntimeError("crash"))
        content = (
            vault / "Needs_Action" / item.quarantined_filename
        ).read_text(encoding="utf-8")
        assert "priority: P0" in content

    def test_logic_error_type(self, executor: ResilientExecutor):
        item = executor.quarantine("test.md", LogicAPIError("bad"))
        assert item.error_type == "logic_error"

    def test_system_error_type(self, executor: ResilientExecutor):
        item = executor.quarantine("test.md", TransientAPIError("timeout"))
        assert item.error_type == "system_error"
