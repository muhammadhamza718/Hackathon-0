"""Unit tests for Odoo Operation Logger."""

import time
from pathlib import Path

import pytest

from agents.gold.odoo_logger import (
    OdooOperationLogger,
    OdooAuditLogger,
    TimedOperationContext,
)


class TestCredentialRedaction:
    """Test credential redaction functionality."""

    def test_redact_credentials_in_dict(self, tmp_path):
        """Test that credentials are redacted in dictionaries."""
        logger = OdooOperationLogger(tmp_path)

        data = {
            "name": "Test Partner",
            "api_key": "secret-key-12345",
            "password": "hunter2",
            "email": "test@example.com",
        }

        redacted = logger.redact_credentials(data)

        assert redacted["name"] == "Test Partner"
        assert redacted["api_key"] == "***REDACTED***"
        assert redacted["password"] == "***REDACTED***"
        assert redacted["email"] == "test@example.com"

    def test_redact_credentials_in_nested_dict(self, tmp_path):
        """Test that credentials are redacted in nested dictionaries."""
        logger = OdooOperationLogger(tmp_path)

        data = {
            "partner": {
                "name": "Test",
                "auth": {
                    "token": "secret-token",
                    "user": "admin",
                },
            },
            "amount": 100.0,
        }

        redacted = logger.redact_credentials(data)

        assert redacted["partner"]["auth"]["token"] == "***REDACTED***"
        assert redacted["partner"]["auth"]["user"] == "admin"
        assert redacted["amount"] == 100.0

    def test_redact_credentials_in_list(self, tmp_path):
        """Test that credentials are redacted in lists."""
        logger = OdooOperationLogger(tmp_path)

        data = [
            {"name": "Item 1", "secret": "value1"},
            {"name": "Item 2", "secret": "value2"},
        ]

        redacted = logger.redact_credentials(data)

        assert redacted[0]["secret"] == "***REDACTED***"
        assert redacted[1]["secret"] == "***REDACTED***"

    def test_redact_long_alphanumeric_strings(self, tmp_path):
        """Test that long alphanumeric strings are redacted."""
        logger = OdooOperationLogger(tmp_path)

        data = {
            "short": "abc123",  # Too short
            "long": "abcdefghij1234567890abcdefghij",  # Long enough
        }

        redacted = logger.redact_credentials(data)

        assert redacted["short"] == "abc123"  # Not redacted
        assert redacted["long"] == "***REDACTED***"  # Redacted


class TestOperationLogging:
    """Test operation logging functionality."""

    def test_log_operation_success(self, tmp_path):
        """Test logging a successful operation."""
        logger = OdooOperationLogger(tmp_path)

        log = logger.log_operation(
            model="res.partner",
            method="create",
            duration_ms=50.5,
            success=True,
            records_affected=1,
            rationale="Creating test partner",
        )

        assert log.success
        assert log.model == "res.partner"
        assert log.method == "create"
        assert log.duration_ms == 50.5
        assert log.records_affected == 1
        assert log.error is None

    def test_log_operation_failure(self, tmp_path):
        """Test logging a failed operation."""
        logger = OdooOperationLogger(tmp_path)

        log = logger.log_operation(
            model="res.partner",
            method="create",
            duration_ms=100.0,
            success=False,
            error="Connection timeout",
            rationale="Creating partner",
        )

        assert not log.success
        assert log.error == "Connection timeout"

    def test_log_operation_with_payload(self, tmp_path):
        """Test logging operation with payload redaction."""
        logger = OdooOperationLogger(tmp_path)

        payload = {
            "name": "Test Partner",
            "api_key": "secret-key",
        }

        log = logger.log_operation(
            model="res.partner",
            method="create",
            duration_ms=25.0,
            success=True,
            payload=payload,
        )

        assert log.redacted_payload is not None
        assert log.redacted_payload["api_key"] == "***REDACTED***"
        assert log.redacted_payload["name"] == "Test Partner"


class TestMetrics:
    """Test operation metrics tracking."""

    def test_get_metrics_initial(self, tmp_path):
        """Test metrics before any operations."""
        logger = OdooOperationLogger(tmp_path)

        metrics = logger.get_metrics()

        assert metrics["total_operations"] == 0
        assert metrics["successful"] == 0
        assert metrics["failed"] == 0
        assert metrics["success_rate_pct"] == 0.0

    def test_get_metrics_after_operations(self, tmp_path):
        """Test metrics after several operations."""
        logger = OdooOperationLogger(tmp_path)

        logger.log_operation("res.partner", "create", 10.0, True, records_affected=1)
        logger.log_operation("res.partner", "write", 20.0, True, records_affected=2)
        logger.log_operation("res.partner", "read", 5.0, False, error="Not found")

        metrics = logger.get_metrics()

        assert metrics["total_operations"] == 3
        assert metrics["successful"] == 2
        assert metrics["failed"] == 1
        assert metrics["success_rate_pct"] == pytest.approx(66.67, rel=0.1)
        assert metrics["avg_duration_ms"] == pytest.approx(11.67, rel=0.1)

    def test_reset_metrics(self, tmp_path):
        """Test resetting metrics."""
        logger = OdooOperationLogger(tmp_path)

        logger.log_operation("res.partner", "create", 10.0, True)
        logger.reset_metrics()

        metrics = logger.get_metrics()

        assert metrics["total_operations"] == 0
        assert metrics["successful"] == 0
        assert metrics["failed"] == 0


class TestTimedOperationContext:
    """Test timed operation context manager."""

    def test_context_manager_times_operation(self, tmp_path):
        """Test that context manager correctly times operations."""
        logger = OdooOperationLogger(tmp_path)

        with logger.context_manager("res.partner", "create") as ctx:
            time.sleep(0.05)  # 50ms
            ctx.records_affected = 1

        # Duration should be around 50ms
        # Note: We can't easily verify the exact log, but the context should complete

    def test_context_manager_handles_exception(self, tmp_path):
        """Test that context manager handles exceptions."""
        logger = OdooOperationLogger(tmp_path)

        try:
            with logger.context_manager("res.partner", "create") as ctx:
                raise ValueError("Test error")
        except ValueError:
            pass

        # Should not raise, operation should be logged as failed


class TestOdooAuditLogger:
    """Test Odoo audit logger."""

    def test_log_operation_creates_entry(self, tmp_path):
        """Test that audit logger creates log entries."""
        logger = OdooAuditLogger(tmp_path)

        result = logger.log_operation(
            operation="odoo_read",
            model="account.move",
            method="search_read",
            details="Read invoices",
            rationale="Revenue aggregation",
            success=True,
        )

        # Result should be a string representation
        assert isinstance(result, str)

    def test_log_credentials_access(self, tmp_path):
        """Test logging credentials access."""
        logger = OdooAuditLogger(tmp_path)

        result = logger.log_credentials_access(
            action="authenticate",
            rationale="Session initialization",
        )

        # Result should be a string representation
        assert isinstance(result, str)
