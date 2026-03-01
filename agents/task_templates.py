"""Task file templates for generating structured vault tasks."""

from __future__ import annotations

from datetime import datetime, timezone


def simple_task_template(title: str, description: str, priority: str = "medium") -> str:
    """Generate a simple task markdown file.

    Args:
        title: Task title.
        description: Task description.
        priority: Priority level.

    Returns:
        Formatted markdown string.
    """
    date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return f"""---
title: {title}
priority: {priority}
created: {date}
status: pending
---
# {title}

Priority: {priority}

## Description
{description}

## Acceptance Criteria
- [ ] Task completed successfully
"""


def hitl_task_template(
    title: str,
    description: str,
    action: str,
    priority: str = "high",
) -> str:
    """Generate a HITL task requiring human approval.

    Args:
        title: Task title.
        description: Task description.
        action: The external action that needs approval.
        priority: Priority level.

    Returns:
        Formatted markdown string.
    """
    date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return f"""---
title: {title}
priority: {priority}
created: {date}
status: pending
requires_approval: true
---
# {title}

Priority: {priority}

## Description
{description}

## External Action Required
{action}

## Approval Status
- [ ] Submitted for approval ✋
- [ ] Human reviewed
- [ ] Action executed
"""
