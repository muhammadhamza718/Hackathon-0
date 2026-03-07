"""Unit tests for Gold Tier autonomous agent.

Comprehensive test coverage for all Gold Tier components including
models, safety gate, audit logger, and resilient executor.
"""

import pytest
from datetime import datetime, timezone

from agents.gold.models import (
    GoldAuditEntry,
    LoopConfig,
    LoopState,
    OdooSession,
    OdooOperation,
    SocialDraft,
    PublishResult,
)
from agents.gold.exceptions import (
    GoldTierError,
    OdooIntegrationError,
    SocialMediaError,
    CircuitBreakerOpenError,
)
from agents.gold.config import (
    OdooConfig as OdooConfigData,
    LoopConfig as LoopConfigData,
    ResilienceConfig,
)
from agents.gold.audit_gold import GoldAuditLogger
from agents.gold.safety_gate import GoldSafetyGate, ApprovalRequest
from agents.gold.resilient_executor import ResilientExecutor, ExecutionResult


# ---------------------------------------------------------------------------
# Model Tests
# ---------------------------------------------------------------------------

class TestGoldAuditEntry:
    """Tests for GoldAuditEntry model."""

    def test_valid_entry_creation(self):
        """Test creating a valid audit entry."""
        entry = GoldAuditEntry(
            timestamp="2026-03-07T12:00:00Z",
            action="triage",
            rationale="Processing inbox item",
        )
        assert entry.action == "triage"
        assert entry.result == "success"
        assert entry.tier == "gold"

    def test_timestamp_validation(self):
        """Test timestamp format validation."""
        with pytest.raises(ValueError, match="Invalid timestamp"):
            GoldAuditEntry(
                timestamp="invalid-date",
                action="triage",
                rationale="Test",
            )

    def test_action_validation(self):
        """Test action validation."""
        with pytest.raises(ValueError, match="Unknown action"):
            GoldAuditEntry(
                timestamp="2026-03-07T12:00:00Z",
                action="invalid_action",
                rationale="Test",
            )

    def test_rationale_validation(self):
        """Test rationale cannot be empty."""
        with pytest.raises(ValueError, match="Rationale cannot be empty"):
            GoldAuditEntry(
                timestamp="2026-03-07T12:00:00Z",
                action="triage",
                rationale="",
            )

    def test_factory_method(self):
        """Test the now() factory method."""
        entry = GoldAuditEntry.now(
            action="triage",
            rationale="Test entry",
        )
        assert entry.timestamp.endswith("Z")
        assert entry.action == "triage"


class TestLoopConfig:
    """Tests for LoopConfig model."""

    def test_default_values(self):
        """Test default configuration values."""
        config = LoopConfig()
        assert config.max_iterations == 1000
        assert config.checkpoint_interval == 1
        assert config.idle_sleep_seconds == 5.0

    def test_positive_validation(self):
        """Test positive integer validation."""
        with pytest.raises(ValueError):
            LoopConfig(max_iterations=-1)


class TestLoopState:
    """Tests for LoopState model."""

    def test_session_id_validation(self):
        """Test session ID validation."""
        with pytest.raises(ValueError, match="Session ID cannot be empty"):
            LoopState(session_id="")

    def test_serialization(self):
        """Test to_dict serialization."""
        state = LoopState(session_id="test_123", iteration=5)
        data = state.to_dict()
        assert data["session_id"] == "test_123"
        assert data["iteration"] == 5

    def test_deserialization(self):
        """Test from_dict deserialization."""
        data = {
            "session_id": "test_456",
            "iteration": 10,
            "blocked_plans": ["plan_1", "plan_2"],
        }
        state = LoopState.from_dict(data)
        assert state.session_id == "test_456"
        assert state.iteration == 10
        assert len(state.blocked_plans) == 2


class TestSocialDraft:
    """Tests for SocialDraft model."""

    def test_platform_validation(self):
        """Test platform validation."""
        with pytest.raises(ValueError, match="Invalid platform"):
            SocialDraft(
                draft_id="test",
                platform="InvalidPlatform",
                content="Test content",
            )

    def test_approval_status_validation(self):
        """Test approval status validation."""
        with pytest.raises(ValueError, match="Invalid status"):
            SocialDraft(
                draft_id="test",
                platform="X",
                content="Test",
                approval_status="invalid",
            )


# ---------------------------------------------------------------------------
# Exception Tests
# ---------------------------------------------------------------------------

class TestExceptions:
    """Tests for exception hierarchy."""

    def test_gold_tier_error(self):
        """Test GoldTierError base exception."""
        with pytest.raises(GoldTierError):
            raise GoldTierError("Base error")

    def test_odoo_integration_error(self):
        """Test OdooIntegrationError."""
        with pytest.raises(OdooIntegrationError):
            raise OdooIntegrationError("Odoo error")

    def test_social_media_error(self):
        """Test SocialMediaError."""
        with pytest.raises(SocialMediaError):
            raise SocialMediaError("Social error")

    def test_circuit_breaker_error(self):
        """Test CircuitBreakerOpenError."""
        error = CircuitBreakerOpenError("test_api")
        assert error.api_name == "test_api"


# ---------------------------------------------------------------------------
# Config Tests
# ---------------------------------------------------------------------------

class TestConfig:
    """Tests for configuration classes."""

    def test_odoo_config_from_env(self, monkeypatch):
        """Test loading Odoo config from environment."""
        monkeypatch.setenv("ODOO_URL", "http://test:8069")
        monkeypatch.setenv("ODOO_DATABASE", "test_db")
        monkeypatch.setenv("ODOO_USERNAME", "test_user")
        monkeypatch.setenv("ODOO_API_KEY", "test_key")

        config = OdooConfigData.from_env()
        assert config.url == "http://test:8069"
        assert config.database == "test_db"

    def test_resilience_config_defaults(self):
        """Test ResilienceConfig default values."""
        config = ResilienceConfig()
        assert config.max_retries == 3
        assert config.base_delay_seconds == 1.0


# ---------------------------------------------------------------------------
# Audit Logger Tests
# ---------------------------------------------------------------------------

class TestGoldAuditLogger:
    """Tests for GoldAuditLogger."""

    def test_log_entry(self, tmp_path):
        """Test logging an audit entry."""
        logger = GoldAuditLogger(logs_dir=str(tmp_path))
        entry = GoldAuditEntry.now(
            action="triage",
            rationale="Test logging",
        )
        logger.log(entry)

        # Verify log file was created
        log_files = list(tmp_path.glob("*.json"))
        assert len(log_files) == 1

    def test_log_action(self, tmp_path):
        """Test the log_action convenience method."""
        logger = GoldAuditLogger(logs_dir=str(tmp_path))
        entry = logger.log_action(
            action="triage",
            rationale="Test action",
        )
        assert entry.result == "success"

    def test_count_by_action(self, tmp_path):
        """Test counting entries by action."""
        logger = GoldAuditLogger(logs_dir=str(tmp_path))
        logger.log_action(action="triage", rationale="Test 1")
        logger.log_action(action="triage", rationale="Test 2")
        logger.log_action(action="complete", rationale="Test 3")

        counts = logger.count_by_action()
        assert counts.get("triage", 0) == 2
        assert counts.get("complete", 0) == 1


# ---------------------------------------------------------------------------
# Safety Gate Tests
# ---------------------------------------------------------------------------

class TestGoldSafetyGate:
    """Tests for GoldSafetyGate."""

    def test_request_approval(self, tmp_path):
        """Test creating an approval request."""
        gate = GoldSafetyGate(approval_dir=str(tmp_path))
        request = gate.request_approval(
            action="odoo_write",
            rationale="Test approval",
            payload={"model": "test", "values": {}},
        )
        assert request.status == "pending"
        assert request.action == "odoo_write"

    def test_approve_request(self, tmp_path):
        """Test approving a request."""
        gate = GoldSafetyGate(approval_dir=str(tmp_path))
        request = gate.request_approval(
            action="odoo_write",
            rationale="Test",
            payload={},
        )

        approved = gate.approve(request.request_id)
        assert approved.status == "approved"
        assert gate.is_approved(request.request_id)

    def test_reject_request(self, tmp_path):
        """Test rejecting a request."""
        gate = GoldSafetyGate(approval_dir=str(tmp_path))
        request = gate.request_approval(
            action="odoo_write",
            rationale="Test",
            payload={},
        )

        rejected = gate.reject(request.request_id, reason="Not needed")
        assert rejected.status == "rejected"

    def test_get_pending_requests(self, tmp_path):
        """Test getting pending requests."""
        gate = GoldSafetyGate(approval_dir=str(tmp_path))
        gate.request_approval(action="odoo_write", rationale="Test 1", payload={})
        gate.request_approval(action="odoo_write", rationale="Test 2", payload={})

        pending = gate.get_pending_requests()
        assert len(pending) == 2

    def test_requires_approval(self, tmp_path):
        """Test checking if action requires approval."""
        gate = GoldSafetyGate(approval_dir=str(tmp_path))
        assert gate.requires_approval("odoo_write")
        assert not gate.requires_approval("odoo_read")


# ---------------------------------------------------------------------------
# Resilient Executor Tests
# ---------------------------------------------------------------------------

class TestResilientExecutor:
    """Tests for ResilientExecutor."""

    def test_successful_execution(self):
        """Test successful function execution."""
        executor = ResilientExecutor()
        result = executor.execute(
            lambda x: x * 2,
            5,
            operation_name="test_op",
        )
        assert result.success
        assert result.value == 10
        assert result.retries_attempted == 0

    def test_retry_on_failure(self):
        """Test retry behavior on failure."""
        executor = ResilienceConfig(max_retries=2)
        exec_instance = ResilientExecutor(config=executor)

        call_count = 0

        def failing_then_success():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("Temporary failure")
            return "success"

        result = exec_instance.execute(
            failing_then_success,
            operation_name="test_retry",
        )
        assert result.success
        assert result.retries_attempted >= 1

    def test_max_retries_exceeded(self):
        """Test max retries exceeded."""
        executor = ResilientExecutor(
            ResilienceConfig(max_retries=2, base_delay_seconds=0.01)
        )

        def always_fails():
            raise ValueError("Always fails")

        result = executor.execute(
            always_fails,
            operation_name="test_max_retries",
        )
        assert not result.success
        assert result.retries_attempted == 2

    def test_execute_or_raise(self):
        """Test execute_or_raise method."""
        executor = ResilientExecutor()

        def success_func():
            return "success"

        result = executor.execute_or_raise(success_func, operation_name="test")
        assert result == "success"

    def test_circuit_breaker_status(self):
        """Test circuit breaker status retrieval."""
        executor = ResilientExecutor()
        status = executor.get_circuit_breaker_status("test_api")
        assert status is None  # Not created yet

        # Trigger creation
        executor.execute(lambda: None, operation_name="test_api")
        status = executor.get_circuit_breaker_status("test_api")
        assert status is not None
        assert status["name"] == "test_api"
