"""Session reconciler — resumes incomplete plans on startup."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from agents.constants import PLANS_DIR, STATUS_ACTIVE, STATUS_BLOCKED, STATUS_DRAFT
from agents.plan_parser import PlanStep, next_pending_step, parse_frontmatter, parse_steps

_STATUS_PRIORITY = {STATUS_ACTIVE: 0, STATUS_BLOCKED: 1, STATUS_DRAFT: 2}


@dataclass(frozen=True)
class ReconcileResult:
    """Immutable result of a session reconciliation run."""

    total_incomplete: int
    next_plan: str | None
    next_step: PlanStep | None

    @property
    def has_work(self) -> bool:
        """True when there are incomplete plans to resume."""
        return self.total_incomplete > 0

    @property
    def next_step_requires_hitl(self) -> bool:
        """True when the next pending step needs human approval."""
        if self.next_step is None:
            return False
        return self.next_step["requires_hitl"]


def find_incomplete_plans(vault_root: Path) -> list[Path]:
    """Find all plans that are not yet complete.

    Scans ``/Plans/`` for files matching ``PLAN-*.md`` whose frontmatter
    status is one of *draft*, *active*, or *blocked*.

    Args:
        vault_root: Root directory of the vault.

    Returns:
        Plan file paths sorted newest-first by filename.
    """
    plans_dir = vault_root / PLANS_DIR
    if not plans_dir.exists():
        return []

    incomplete: list[Path] = []
    for plan_file in sorted(plans_dir.glob("PLAN-*.md"), reverse=True):
        content = plan_file.read_text(encoding="utf-8")
        meta = parse_frontmatter(content)
        if meta["status"] in _STATUS_PRIORITY:
            incomplete.append(plan_file)

    return incomplete


def prioritize_plans(plans: list[Path]) -> list[Path]:
    """Sort plans by status priority: active > blocked > draft.

    Args:
        plans: List of plan file paths.

    Returns:
        Sorted list with highest priority first.
    """

    def _sort_key(p: Path) -> tuple[int, str]:
        content = p.read_text(encoding="utf-8")
        meta = parse_frontmatter(content)
        return (_STATUS_PRIORITY.get(meta["status"], 99), p.name)

    return sorted(plans, key=_sort_key)


def reconcile(vault_root: Path) -> ReconcileResult:
    """Run startup reconciliation — find and prioritize incomplete plans.

    Args:
        vault_root: Root directory of the vault.

    Returns:
        A ``ReconcileResult`` with the top-priority plan and its next step.
    """
    plans = find_incomplete_plans(vault_root)
    if not plans:
        return ReconcileResult(total_incomplete=0, next_plan=None, next_step=None)

    prioritized = prioritize_plans(plans)
    top = prioritized[0]
    content = top.read_text(encoding="utf-8")
    steps = parse_steps(content)
    pending = next_pending_step(steps)

    return ReconcileResult(
        total_incomplete=len(plans),
        next_plan=top.name,
        next_step=pending,
    )
