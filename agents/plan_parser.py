"""Utility for parsing Silver Tier Plan files."""

from __future__ import annotations

import re
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
