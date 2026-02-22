"""
Complexity Detector: Identifies complex tasks that warrant Plan.md creation.

Analyzes user input against keyword heuristics to determine if a task
requires structured planning (Plan.md) or can be executed directly.

Functions:
    detect_complexity() - Analyze task input and return complexity assessment
    extract_keywords() - Extract matched keywords from input
    is_multi_step() - Detect multi-step task indicators
    is_external_action() - Detect external action requirements
"""

import logging
import re
from dataclasses import dataclass
from enum import Enum
from typing import Set, List, Tuple

logger = logging.getLogger(__name__)


class ComplexityLevel(Enum):
    """Complexity classification."""
    SIMPLE = "simple"
    COMPLEX = "complex"


@dataclass
class ComplexityAssessment:
    """Result of complexity analysis."""
    level: ComplexityLevel
    matched_keywords: List[str]
    reasoning: str
    suggestion: str

    def is_complex(self) -> bool:
        """Check if task is complex."""
        return self.level == ComplexityLevel.COMPLEX


class ComplexityDetector:
    """Detects task complexity and recommends Plan.md creation."""

    # Keyword categories
    HIGH_PRIORITY_KEYWORDS = {
        '#high', 'urgent', 'asap', 'critical', 'immediately',
        'priority', 'emergency', 'deadline'
    }

    MULTI_STEP_KEYWORDS = {
        'invoice', 'payment', 'client', 'project', 'campaign',
        'report', 'audit', 'schedule', 'coordinate', 'plan',
        'workflow', 'process', 'procedure', 'sequence'
    }

    EXTERNAL_ACTION_KEYWORDS = {
        'send', 'post', 'publish', 'email', 'message', 'call',
        'pay', 'submit', 'upload', 'integrate', 'notify',
        'notify', 'alert', 'ping', 'broadcast'
    }

    DEPENDENCY_KEYWORDS = {
        'after', 'once', 'then', 'require', 'depend', 'pipeline',
        'sequence', 'chain', 'before', 'until', 'when'
    }

    MULTI_STAKEHOLDER_KEYWORDS = {
        'client', 'team', 'manager', 'approval', 'sign-off',
        'review', 'stakeholder', 'owner', 'approver', 'recipient'
    }

    # Simple task indicators (no plan needed)
    SIMPLE_TASK_KEYWORDS = {
        'read', 'show', 'display', 'summarize', 'what',
        'how many', 'list', 'find', 'search', 'get',
        'explain', 'describe', 'tell me'
    }

    def assess_complexity(self, user_input: str) -> ComplexityAssessment:
        """
        Analyze user input and determine if it requires planning.

        Args:
            user_input: Raw user task description

        Returns:
            ComplexityAssessment with level, keywords, reasoning, suggestion
        """
        if not user_input or not user_input.strip():
            return ComplexityAssessment(
                level=ComplexityLevel.SIMPLE,
                matched_keywords=[],
                reasoning="Empty input",
                suggestion="No task provided."
            )

        normalized_input = user_input.lower()
        matched_keywords: List[str] = []

        # Check for simple task indicators first
        simple_matches = self._match_keywords(normalized_input, self.SIMPLE_TASK_KEYWORDS)
        if simple_matches and len(simple_matches) >= 1:
            logger.info(f"Detected simple task indicators: {simple_matches}")
            return ComplexityAssessment(
                level=ComplexityLevel.SIMPLE,
                matched_keywords=simple_matches,
                reasoning=f"Single-action task detected. Keywords: {', '.join(simple_matches)}",
                suggestion="Executing directly (no plan needed)."
            )

        # Detect complexity indicators
        priority_matches = self._match_keywords(normalized_input, self.HIGH_PRIORITY_KEYWORDS)
        multi_step_matches = self._match_keywords(normalized_input, self.MULTI_STEP_KEYWORDS)
        external_matches = self._match_keywords(normalized_input, self.EXTERNAL_ACTION_KEYWORDS)
        dependency_matches = self._match_keywords(normalized_input, self.DEPENDENCY_KEYWORDS)
        stakeholder_matches = self._match_keywords(normalized_input, self.MULTI_STAKEHOLDER_KEYWORDS)

        matched_keywords.extend(priority_matches)
        matched_keywords.extend(multi_step_matches)
        matched_keywords.extend(external_matches)
        matched_keywords.extend(dependency_matches)
        matched_keywords.extend(stakeholder_matches)

        # Complexity threshold: 2+ indicators or external action + another indicator
        is_complex = (
            len(matched_keywords) >= 2 or
            (len(external_matches) > 0 and len(multi_step_matches) > 0) or
            len(priority_matches) > 0 and len(external_matches) > 0
        )

        if is_complex:
            logger.info(f"Detected complex task. Keywords: {matched_keywords}")
            reasoning_parts = []
            if priority_matches:
                reasoning_parts.append(f"high-priority markers ({', '.join(priority_matches)})")
            if multi_step_matches:
                reasoning_parts.append(f"multi-step indicators ({', '.join(multi_step_matches)})")
            if external_matches:
                reasoning_parts.append(f"external actions ({', '.join(external_matches)})")
            if dependency_matches:
                reasoning_parts.append(f"dependencies ({', '.join(dependency_matches)})")
            if stakeholder_matches:
                reasoning_parts.append(f"multiple stakeholders ({', '.join(stakeholder_matches)})")

            reasoning = f"Complex task detected: {', '.join(reasoning_parts)}"
            suggestion = "I should create a plan for this task to organize the steps, track progress, and ensure all approvals are obtained."

            return ComplexityAssessment(
                level=ComplexityLevel.COMPLEX,
                matched_keywords=matched_keywords,
                reasoning=reasoning,
                suggestion=suggestion
            )

        # Default to simple if no complexity indicators
        return ComplexityAssessment(
            level=ComplexityLevel.SIMPLE,
            matched_keywords=matched_keywords,
            reasoning="No complexity indicators detected",
            suggestion="Executing directly (no plan needed)."
        )

    def extract_steps_from_input(self, user_input: str) -> List[str]:
        """
        Extract potential action steps from user input.

        Looks for:
        - Numbered lists (1., 2., 3., etc.)
        - Bullet points (-, *, •)
        - Sentences ending with periods (crude heuristic)

        Args:
            user_input: Raw user input

        Returns:
            List of extracted steps (or empty if none found)
        """
        steps: List[str] = []

        # Try numbered list format
        numbered_pattern = r'^\s*\d+\.\s+(.+)$'
        numbered_matches = re.findall(numbered_pattern, user_input, re.MULTILINE)
        if numbered_matches:
            steps.extend(numbered_matches)
            return steps

        # Try bullet point format
        bullet_pattern = r'^\s*[-*•]\s+(.+)$'
        bullet_matches = re.findall(bullet_pattern, user_input, re.MULTILINE)
        if bullet_matches:
            steps.extend(bullet_matches)
            return steps

        # Fallback: split by sentence (crude heuristic)
        # Only if no structured format found
        if not steps and len(user_input) > 50:
            # Split by sentence-ending punctuation
            sentences = re.split(r'[.!?]\s+', user_input)
            steps = [s.strip() for s in sentences if s.strip() and len(s.strip()) > 10]
            # Limit to first 5 steps
            steps = steps[:5]

        return steps

    def _match_keywords(self, text: str, keywords: Set[str]) -> List[str]:
        """
        Match keywords in text.

        Args:
            text: Normalized text to search
            keywords: Set of keywords to find

        Returns:
            List of matched keywords
        """
        matched = []
        for keyword in keywords:
            # Use word boundary matching for accuracy
            pattern = r'\b' + re.escape(keyword) + r'\b'
            if re.search(pattern, text, re.IGNORECASE):
                matched.append(keyword)

        return matched


def detect_complexity(user_input: str) -> ComplexityAssessment:
    """
    Convenience function to detect complexity without instantiating class.

    Args:
        user_input: Raw user task description

    Returns:
        ComplexityAssessment with level and reasoning
    """
    detector = ComplexityDetector()
    return detector.assess_complexity(user_input)


def extract_steps(user_input: str) -> List[str]:
    """
    Convenience function to extract steps from user input.

    Args:
        user_input: Raw user task description

    Returns:
        List of extracted steps
    """
    detector = ComplexityDetector()
    return detector.extract_steps_from_input(user_input)
