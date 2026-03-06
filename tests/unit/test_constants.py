"""Unit tests for agents.constants module."""

from __future__ import annotations

import pytest

from agents.constants import (
    APPROVED_DIR,
    DASHBOARD_FILE,
    DONE_DIR,
    HITL_MARKER,
    INBOX_DIR,
    NEEDS_ACTION_DIR,
    PENDING_APPROVAL_DIR,
    PLANS_DIR,
    PLAN_FILE_PATTERN,
    PLAN_FILE_PREFIX,
    PRIORITY_HIGH,
    PRIORITY_LOW,
    PRIORITY_MEDIUM,
    REJECTED_DIR,
    STATUS_ACTIVE,
    STATUS_APPROVED,
    STATUS_BLOCKED,
    STATUS_COMPLETE,
    STATUS_DRAFT,
    STATUS_REJECTED,
    STEP_DONE_MARKER,
    STEP_PENDING_MARKER,
    TIER_BRONZE,
    TIER_SILVER,
    Tier,
)


def test_vault_dirs_are_strings():
    for val in [INBOX_DIR, NEEDS_ACTION_DIR, DONE_DIR, PENDING_APPROVAL_DIR,
                PLANS_DIR, APPROVED_DIR, REJECTED_DIR]:
        assert isinstance(val, str)
        assert len(val) > 0


def test_plan_prefix_and_pattern():
    assert PLAN_FILE_PREFIX == "PLAN-"
    assert PLAN_FILE_PATTERN.startswith("PLAN-")
    assert PLAN_FILE_PATTERN.endswith(".md")


def test_status_values_unique():
    statuses = {STATUS_DRAFT, STATUS_ACTIVE, STATUS_BLOCKED,
                STATUS_COMPLETE, STATUS_APPROVED, STATUS_REJECTED}
    assert len(statuses) == 6


def test_priority_values():
    assert PRIORITY_HIGH != PRIORITY_MEDIUM
    assert PRIORITY_MEDIUM != PRIORITY_LOW


def test_hitl_marker():
    assert HITL_MARKER == "✋"


def test_step_markers():
    assert STEP_DONE_MARKER == "[x]"
    assert STEP_PENDING_MARKER == "[ ]"


def test_tier_names():
    assert TIER_BRONZE == "bronze"
    assert TIER_SILVER == "silver"


def test_dashboard_file():
    assert DASHBOARD_FILE == "Dashboard.md"


class TestTierEnum:
    """Verify Tier enum values and capability properties."""

    @pytest.mark.parametrize(
        "tier,expected_hitl",
        [
            (Tier.BRONZE, False),
            (Tier.SILVER, True),
            (Tier.GOLD, True),
        ],
    )
    def test_can_use_hitl(self, tier: Tier, expected_hitl: bool):
        assert tier.can_use_hitl is expected_hitl

    @pytest.mark.parametrize(
        "tier,expected_external",
        [
            (Tier.BRONZE, False),
            (Tier.SILVER, False),
            (Tier.GOLD, True),
        ],
    )
    def test_can_act_externally(self, tier: Tier, expected_external: bool):
        assert tier.can_act_externally is expected_external

    def test_values_match_string_constants(self):
        assert Tier.BRONZE.value == TIER_BRONZE
        assert Tier.SILVER.value == TIER_SILVER
