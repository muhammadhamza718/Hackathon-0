"""Unit tests for agents.exceptions module."""

from __future__ import annotations

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


class TestExceptionMessages:
    def test_can_raise_with_message(self):
        try:
            raise VaultStructureError("Missing Inbox directory")
        except VaultStructureError as e:
            assert "Missing Inbox" in str(e)

    def test_catch_by_base(self):
        try:
            raise PlanNotFoundError("PLAN-2026-001 not found")
        except AgentError as e:
            assert "PLAN-2026-001" in str(e)
