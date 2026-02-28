"""Session reconciler — resumes incomplete plans on startup."""

from __future__ import annotations

from pathlib import Path

from agents.constants import PLANS_DIR, STATUS_ACTIVE, STATUS_BLOCKED, STATUS_DRAFT
from agents.plan_parser import next_pending_step, parse_frontmatter, parse_steps


def find_incomplete_plans(vault_root: Path) -> list[Path]:
    """Find all plans that are not yet complete.

    Args:
        vault_root: Root directory of the vault.

    Returns:
        List of plan file paths sorted by priority then date (newest first).
    """
    plans_dir = vault_root / PLANS_DIR
    if not plans_dir.exists():
        return []

    incomplete = []
    for plan_file in sorted(plans_dir.glob("PLAN-*.md"), reverse=True):
        content = plan_file.read_text(encoding="utf-8")
        meta = parse_frontmatter(content)
        if meta["status"] in (STATUS_DRAFT, STATUS_ACTIVE, STATUS_BLOCKED):
            incomplete.append(plan_file)

    return incomplete


def prioritize_plans(plans: list[Path]) -> list[Path]:
    """Sort plans by status priority: active > blocked > draft.

    Args:
        plans: List of plan file paths.

    Returns:
        Sorted list with highest priority first.
    """
    priority_order = {STATUS_ACTIVE: 0, STATUS_BLOCKED: 1, STATUS_DRAFT: 2}

    def sort_key(p: Path) -> tuple[int, str]:
        content = p.read_text(encoding="utf-8")
        meta = parse_frontmatter(content)
        return (priority_order.get(meta["status"], 99), p.name)

    return sorted(plans, key=sort_key)


def reconcile(vault_root: Path) -> dict:
    """Run startup reconciliation — find and prioritize incomplete plans.

    Args:
        vault_root: Root directory of the vault.

    Returns:
        Dict with keys: total_incomplete, next_plan, next_step
    """
    plans = find_incomplete_plans(vault_root)
    if not plans:
        return {"total_incomplete": 0, "next_plan": None, "next_step": None}

    prioritized = prioritize_plans(plans)
    top = prioritized[0]
    content = top.read_text(encoding="utf-8")
    steps = parse_steps(content)
    pending = next_pending_step(steps)

    return {
        "total_incomplete": len(plans),
        "next_plan": top.name,
        "next_step": pending,
    }
