"""Task complexity detection for routing decisions."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class ComplexityResult:
    """Result of complexity analysis."""
    level: str  # "simple" or "complex"
    score: int  # 0-10 complexity score
    reasons: list[str]  # Why it's complex


# Patterns that signal complexity
COMPLEX_PATTERNS = [
    (r"(?i)\bemail\b", "external email action"),
    (r"(?i)\bapi\s+call\b", "API integration"),
    (r"(?i)\bpayment\b", "payment processing"),
    (r"(?i)\bdeploy\b", "deployment action"),
    (r"(?i)\bpublish\b", "publishing action"),
    (r"(?i)\bsend\b", "external send action"),
    (r"(?i)\bmulti[- ]?step\b", "multi-step workflow"),
    (r"(?i)\bexternal\b", "external system interaction"),
    (r"✋", "HITL marker present"),
    (r"(?i)\bapproval\b", "requires approval"),
    (r"(?i)\bdatabase\b", "database operation"),
    (r"(?i)\bmigrat", "migration work"),
]

# Patterns for step counting
STEP_PATTERN = re.compile(r"^[-*]\s+\[[ x]\]", re.MULTILINE | re.IGNORECASE)


def detect_complexity(content: str) -> ComplexityResult:
    """Analyze task content for complexity signals.

    Args:
        content: Markdown content of the task file.

    Returns:
        ComplexityResult with level, score, and reasons.
    """
    score = 0
    reasons: list[str] = []

    # Check pattern signals
    for pattern, reason in COMPLEX_PATTERNS:
        if re.search(pattern, content):
            score += 2
            reasons.append(reason)

    # Check step count
    steps = len(STEP_PATTERN.findall(content))
    if steps > 5:
        score += 2
        reasons.append(f"{steps} steps detected")
    elif steps > 3:
        score += 1

    # Check content length (long tasks tend to be complex)
    word_count = len(content.split())
    if word_count > 300:
        score += 1
        reasons.append("lengthy description")

    level = "complex" if score >= 3 else "simple"
    return ComplexityResult(level=level, score=min(score, 10), reasons=reasons)
