"""Unit tests for agents.exceptions module."""

from __future__ import annotations

import pytest

from agents.exceptions import (
    AgentError,
    ApprovalTimeoutError,
    ConfigurationError,
    FileRoutingError,
    HITLError,
    PlanError,
    PlanNotFoundError,
    PlanValidationError,
    ReconciliationError,
    ScanError,
    TemplateError,
    VaultError,
    VaultStructureError,
)


class TestExceptionHierarchy:
    def test_vault_error_is_agent_error(self):
        assert issubclass(VaultError, AgentError)

    def test_vault_structure_is_vault_error(self):
        assert issubclass(VaultStructureError, VaultError)

    def test_file_routing_is_vault_error(self):
        assert issubclass(FileRoutingError, VaultError)

    def test_plan_error_is_agent_error(self):
        assert issubclass(PlanError, AgentError)

    def test_plan_not_found_is_plan_error(self):
        assert issubclass(PlanNotFoundError, PlanError)

    def test_plan_validation_is_plan_error(self):
        assert issubclass(PlanValidationError, PlanError)

    def test_hitl_error_is_agent_error(self):
        assert issubclass(HITLError, AgentError)

    def test_approval_timeout_is_hitl_error(self):
        assert issubclass(ApprovalTimeoutError, HITLError)

    def test_reconciliation_is_agent_error(self):
        assert issubclass(ReconciliationError, AgentError)

    def test_configuration_is_agent_error(self):
        assert issubclass(ConfigurationError, AgentError)


class TestShortName:
    """Verify short_name property across exception hierarchy."""

    @pytest.mark.parametrize(
        "exc_cls,expected_name",
        [
            (AgentError, "AgentError"),
            (VaultError, "VaultError"),
            (VaultStructureError, "VaultStructureError"),
            (FileRoutingError, "FileRoutingError"),
            (PlanNotFoundError, "PlanNotFoundError"),
            (ApprovalTimeoutError, "ApprovalTimeoutError"),
            (ScanError, "ScanError"),
            (TemplateError, "TemplateError"),
        ],
    )
    def test_short_name(self, exc_cls: type, expected_name: str):
        err = exc_cls("test message")
        assert err.short_name == expected_name


class TestExceptionMessages:
    def test_can_raise_with_message(self):
        with pytest.raises(VaultStructureError, match="Missing Inbox"):
            raise VaultStructureError("Missing Inbox directory")

    def test_catch_by_base(self):
        with pytest.raises(AgentError, match="PLAN-2026-001"):
            raise PlanNotFoundError("PLAN-2026-001 not found")
