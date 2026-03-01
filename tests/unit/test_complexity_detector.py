"""Unit tests for agents.complexity_detector module."""

from __future__ import annotations

from agents.complexity_detector import detect_complexity


class TestDetectComplexity:
    def test_simple_task(self):
        result = detect_complexity("# Fix typo\nCorrect the spelling.")
        assert result.level == "simple"
        assert result.score < 3

    def test_complex_with_email(self):
        result = detect_complexity("Send an email to the client with the report.")
        assert result.level == "complex"
        assert "external email action" in result.reasons or "external send action" in result.reasons

    def test_complex_with_api_call(self):
        result = detect_complexity("Make an API call to fetch data.")
        assert result.level == "complex"

    def test_complex_with_hitl(self):
        result = detect_complexity("Step 2: Execute ✋")
        assert result.level == "complex"
        assert "HITL marker present" in result.reasons

    def test_complex_multi_step(self):
        content = "This is a multi-step process with deployment."
        result = detect_complexity(content)
        assert result.level == "complex"

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
        assert result.level == "simple"
        assert result.reasons == []
