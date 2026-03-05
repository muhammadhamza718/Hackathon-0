"""Task file templates for generating structured vault tasks."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum, unique


@unique
class TemplateType(Enum):
    """Available task template types."""

    SIMPLE = "simple"
    HITL = "hitl"


def render_template(
    template_type: TemplateType,
    title: str,
    description: str,
    priority: str = "medium",
    action: str = "",
) -> str:
    """Render a task template by type.

    Args:
        template_type: Which template to use.
        title: Task title.
        description: Task description.
        priority: Priority level.
        action: External action (required for HITL templates).

    Returns:
        Formatted markdown string.
    """
    if template_type is TemplateType.HITL:
        return hitl_task_template(title, description, action=action, priority=priority)
    return simple_task_template(title, description, priority=priority)


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
