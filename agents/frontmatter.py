"""YAML frontmatter parser and writer for vault markdown files."""

from __future__ import annotations

import re
from typing import Any


def parse(content: str) -> dict[str, str]:
    """Parse YAML-like frontmatter from markdown content.

    Args:
        content: Full file content with --- delimiters.

    Returns:
        Dict of key-value pairs from frontmatter.
    """
    match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    if not match:
        return {}
    result: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if ":" in line:
            key, _, value = line.partition(":")
            result[key.strip()] = value.strip()
    return result


def update_field(content: str, field: str, new_value: str) -> str:
    """Update a single frontmatter field value.

    Args:
        content: Full file content.
        field: Field name to update.
        new_value: New value for the field.

    Returns:
        Updated content string.
    """
    pattern = rf"^{re.escape(field)}:\s*.*$"
    replacement = f"{field}: {new_value}"
    return re.sub(pattern, replacement, content, count=1, flags=re.MULTILINE)


def build(fields: dict[str, Any]) -> str:
    """Build a YAML frontmatter block.

    Args:
        fields: Dict of key-value pairs.

    Returns:
        Frontmatter string with --- delimiters.
    """
    lines = ["---"]
    for key, value in fields.items():
        lines.append(f"{key}: {value}")
    lines.append("---")
    return "\n".join(lines)
