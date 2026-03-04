"""Utility for parsing Silver Tier Plan files."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import TypedDict


class PlanStep(TypedDict):
    index: int
    description: str
    done: bool
    requires_hitl: bool


class PlanMeta(TypedDict):
    task_id: str
    status: str
    priority: str


def parse_frontmatter(content: str) -> PlanMeta:
    """Extract YAML-like frontmatter from a plan file.

    Args:
        content: Raw file content.

    Returns:
        Dict with task_id, status, priority keys.
    """
    meta: PlanMeta = {"task_id": "", "status": "", "priority": ""}
    match = re.search(r"^---\n(.*?)\n---", content, re.DOTALL)
    if not match:
        return meta
    for line in match.group(1).splitlines():
        if ":" in line:
            key, _, value = line.partition(":")
            key = key.strip()
            value = value.strip()
            if key in meta:
                meta[key] = value  # type: ignore[literal-required]
    return meta


def parse_steps(content: str) -> list[PlanStep]:
    """Extract roadmap steps from a plan file.

    Args:
        content: Raw file content.

    Returns:
        List of PlanStep dicts in order.
    """
    steps: list[PlanStep] = []
    pattern = re.compile(r"- \[(x| )\] (.+)", re.IGNORECASE)
    for i, match in enumerate(pattern.finditer(content)):
        done = match.group(1).lower() == "x"
        description = match.group(2).strip()
        requires_hitl = "✋" in description
        steps.append(
            PlanStep(
                index=i,
                description=description,
                done=done,
                requires_hitl=requires_hitl,
            )
        )
    return steps


def next_pending_step(steps: list[PlanStep]) -> PlanStep | None:
    """Return the first incomplete step, or None if all done."""
    for step in steps:
        if not step["done"]:
            return step
    return None


@dataclass(frozen=True)
class PlanSummary:
    """Immutable summary of a parsed plan file."""

    meta: PlanMeta
    steps: list[PlanStep]
    total_steps: int
    completed_steps: int

    @property
    def progress_pct(self) -> float:
        """Completion percentage (0.0 to 100.0)."""
        if self.total_steps == 0:
            return 0.0
        return round(self.completed_steps / self.total_steps * 100, 1)

    @property
    def is_complete(self) -> bool:
        """True when all steps are done."""
        return self.total_steps > 0 and self.completed_steps == self.total_steps

    @property
    def next_step(self) -> PlanStep | None:
        """The first incomplete step, if any."""
        return next_pending_step(self.steps)


def summarize_plan(content: str) -> PlanSummary:
    """Parse a plan file into a high-level summary.

    Args:
        content: Raw plan file content.

    Returns:
        A ``PlanSummary`` with metadata, steps, and progress info.
    """
    meta = parse_frontmatter(content)
    steps = parse_steps(content)
    completed = sum(1 for s in steps if s["done"])
    return PlanSummary(
        meta=meta,
        steps=steps,
        total_steps=len(steps),
        completed_steps=completed,
    )
