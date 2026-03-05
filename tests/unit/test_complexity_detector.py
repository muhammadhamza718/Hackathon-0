"""Unit tests for agents.complexity_detector module."""

from __future__ import annotations

import pytest

from agents.complexity_detector import ComplexityLevel, ComplexityResult, detect_complexity


class TestComplexityLevel:
    """Verify ComplexityLevel enum behavior."""

    def test_simple_less_than_complex(self):
        assert ComplexityLevel.SIMPLE < ComplexityLevel.COMPLEX

    def test_from_score_below_threshold(self):
        assert ComplexityLevel.from_score(2) is ComplexityLevel.SIMPLE

    def test_from_score_at_threshold(self):
        assert ComplexityLevel.from_score(3) is ComplexityLevel.COMPLEX

    def test_from_score_above_threshold(self):
        assert ComplexityLevel.from_score(8) is ComplexityLevel.COMPLEX

    @pytest.mark.parametrize(
        "score,threshold,expected",
        [
            (0, 3, ComplexityLevel.SIMPLE),
            (3, 3, ComplexityLevel.COMPLEX),
            (5, 6, ComplexityLevel.SIMPLE),
            (6, 6, ComplexityLevel.COMPLEX),
        ],
    )
    def test_from_score_custom_threshold(
        self, score: int, threshold: int, expected: ComplexityLevel
    ):
        assert ComplexityLevel.from_score(score, threshold) is expected


class TestComplexityResult:
    """Verify frozen ComplexityResult dataclass."""

    def test_is_complex_true(self):
        result = ComplexityResult(
            level=ComplexityLevel.COMPLEX, score=5, reasons=("api",)
        )
        assert result.is_complex is True

    def test_is_complex_false(self):
        result = ComplexityResult(
            level=ComplexityLevel.SIMPLE, score=1, reasons=()
        )
        assert result.is_complex is False

    def test_frozen(self):
        result = ComplexityResult(
            level=ComplexityLevel.SIMPLE, score=0, reasons=()
        )
        with pytest.raises(AttributeError):
            result.score = 5  # type: ignore[misc]

    def test_reasons_is_tuple(self):
        result = detect_complexity("Send email via API")
        assert isinstance(result.reasons, tuple)


class TestDetectComplexity:
    def test_simple_task(self):
        result = detect_complexity("# Fix typo\nCorrect the spelling.")
        assert result.level is ComplexityLevel.SIMPLE
        assert result.score < 3

    def test_complex_with_email(self):
        result = detect_complexity("Send an email to the client with the report.")
        assert result.level is ComplexityLevel.COMPLEX

    def test_complex_with_api_call(self):
        result = detect_complexity("Make an API call to fetch data.")
        assert result.level is ComplexityLevel.COMPLEX

    def test_complex_with_hitl(self):
        result = detect_complexity("Step 2: Execute ✋")
        assert result.level is ComplexityLevel.COMPLEX
        assert "HITL marker present" in result.reasons

    def test_complex_multi_step(self):
        content = "This is a multi-step process with deployment."
        result = detect_complexity(content)
        assert result.level is ComplexityLevel.COMPLEX

    def test_score_capped_at_10(self):
        content = "Send email, call API, make payment, deploy, publish, external multi-step database migration ✋ approval"
        result = detect_complexity(content)
        assert result.score <= 10

    def test_many_steps_increases_score(self):
        steps = "\n".join(f"- [ ] Step {i}" for i in range(8))
        result = detect_complexity(f"# Task\n{steps}")
        assert result.score > 0
        assert "8 steps detected" in result.reasons

    def test_short_simple(self):
        result = detect_complexity("Fix a bug.")
        assert result.level is ComplexityLevel.SIMPLE
        assert result.reasons == ()
