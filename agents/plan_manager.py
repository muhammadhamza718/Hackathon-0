"""Plan file creation and management for Silver Tier."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from agents.constants import PLANS_DIR, STATUS_DRAFT
from agents.utils import ensure_dir


def next_plan_id(vault_root: Path) -> str:
    """Generate the next plan ID based on existing plans.

    Format: PLAN-YYYY-NNN (e.g. PLAN-2026-001)

    Args:
        vault_root: Root directory of the vault.

    Returns:
        Next available plan ID string.
    """
    plans_dir = vault_root / PLANS_DIR
    year = datetime.now(timezone.utc).strftime("%Y")

    existing = sorted(plans_dir.glob(f"PLAN-{year}-*.md"))
    if not existing:
        return f"PLAN-{year}-001"

    last = existing[-1].stem  # e.g. PLAN-2026-003
    parts = last.split("-")
    num = int(parts[-1]) + 1
    return f"PLAN-{year}-{num:03d}"


def create_plan(
    vault_root: Path,
    objective: str,
    steps: list[str],
    priority: str = "medium",
) -> Path:
    """Create a new Plan file in the vault.

    Args:
        vault_root: Root directory of the vault.
        objective: Plan objective description.
        steps: List of step descriptions.
        priority: Priority level (high, medium, low).

    Returns:
        Path to the created plan file.
    """
    plans_dir = ensure_dir(vault_root / PLANS_DIR)
    plan_id = next_plan_id(vault_root)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    step_lines = "\n".join(f"- [ ] {s}" for s in steps)

    content = f"""---
task_id: {plan_id}
status: {STATUS_DRAFT}
priority: {priority}
created_date: {now}
---
# Objective
{objective}

## Roadmap
{step_lines}

## Reasoning Logs
- [{now}] Plan created.
"""

    path = plans_dir / f"{plan_id}.md"
    path.write_text(content, encoding="utf-8")
    return path


def update_plan_status(plan_path: Path, new_status: str) -> None:
    """Update the status field in a plan file's frontmatter.

    Args:
        plan_path: Path to the plan file.
        new_status: New status value.
    """
    content = plan_path.read_text(encoding="utf-8")
    import re
    content = re.sub(
        r"^status:\s*\S+",
        f"status: {new_status}",
        content,
        count=1,
        flags=re.MULTILINE,
    )
    plan_path.write_text(content, encoding="utf-8")
