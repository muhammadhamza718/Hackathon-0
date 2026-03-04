"""Unit tests for agents.vault_router module."""

from __future__ import annotations

from pathlib import Path

import pytest

from agents.vault_router import (
    ClassificationResult,
    TaskClassification,
    classify_task,
    classify_task_detailed,
    mark_done,
    route_file,
)


@pytest.fixture
def vault(tmp_path: Path) -> Path:
    for d in ("Inbox", "Needs_Action", "Done", "Pending_Approval"):
        (tmp_path / d).mkdir()
    return tmp_path


class TestTaskClassification:
    """Verify the TaskClassification enum values and identity."""

    def test_simple_value(self):
        assert TaskClassification.SIMPLE.value == "simple"

    def test_complex_value(self):
        assert TaskClassification.COMPLEX.value == "complex"

    def test_enum_members_are_unique(self):
        values = [m.value for m in TaskClassification]
        assert len(values) == len(set(values))


class TestClassificationResult:
    """Verify the frozen ClassificationResult dataclass."""

    def test_is_complex_true(self):
        result = ClassificationResult(
            classification=TaskClassification.COMPLEX,
            matched_signals=("involves API interaction",),
        )
        assert result.is_complex is True

    def test_is_complex_false(self):
        result = ClassificationResult(
            classification=TaskClassification.SIMPLE,
            matched_signals=(),
        )
        assert result.is_complex is False

    def test_frozen(self):
        result = ClassificationResult(
            classification=TaskClassification.SIMPLE,
            matched_signals=(),
        )
        with pytest.raises(AttributeError):
            result.classification = TaskClassification.COMPLEX  # type: ignore[misc]

    def test_matched_signals_tuple(self):
        result = ClassificationResult(
            classification=TaskClassification.COMPLEX,
            matched_signals=("reason a", "reason b"),
        )
        assert isinstance(result.matched_signals, tuple)
        assert len(result.matched_signals) == 2


class TestClassifyTask:
    def test_simple_task(self):
        assert classify_task("# Fix typo\n\nCorrect the spelling.") is TaskClassification.SIMPLE

    def test_complex_with_email(self):
        assert classify_task("Send an email to the client.") is TaskClassification.COMPLEX

    def test_complex_with_api(self):
        assert classify_task("Call the payment API.") is TaskClassification.COMPLEX

    def test_complex_with_hitl_marker(self):
        assert classify_task("Step 2: Execute ✋") is TaskClassification.COMPLEX

    def test_complex_multi_step(self):
        assert classify_task("This is a multi-step process.") is TaskClassification.COMPLEX


class TestClassifyTaskDetailed:
    """Verify classify_task_detailed returns reasoning trails."""

    def test_simple_has_no_signals(self):
        result = classify_task_detailed("# Simple task\n\nJust a note.")
        assert result.classification is TaskClassification.SIMPLE
        assert result.matched_signals == ()

    def test_complex_captures_all_signals(self):
        content = "Send email via API for external payment ✋ multi-step"
        result = classify_task_detailed(content)
        assert result.is_complex
        assert len(result.matched_signals) >= 5

    @pytest.mark.parametrize(
        "content,expected_signal",
        [
            ("Call the external service", "references external system"),
            ("Use the REST API", "involves API interaction"),
            ("Send email notification", "requires sending email"),
            ("Process payment", "involves payment processing"),
            ("A multi-step workflow", "multi-step workflow"),
            ("Approve step ✋", "HITL marker present"),
        ],
    )
    def test_individual_signal_detection(self, content: str, expected_signal: str):
        result = classify_task_detailed(content)
        assert expected_signal in result.matched_signals


class TestRouteFile:
    def test_simple_routed_to_needs_action(self, vault: Path):
        f = vault / "Inbox" / "task.md"
        f.write_text("# Simple task\n\nDo something.")
        dest = route_file(f, vault)
        assert dest.parent.name == "Needs_Action"
        assert not f.exists()

    def test_complex_routed_to_pending(self, vault: Path):
        f = vault / "Inbox" / "task.md"
        f.write_text("# Send email to client\n\nEmail the report.")
        dest = route_file(f, vault)
        assert dest.parent.name == "Pending_Approval"

    def test_missing_file_raises(self, vault: Path):
        with pytest.raises(FileNotFoundError):
            route_file(vault / "Inbox" / "nope.md", vault)


class TestMarkDone:
    def test_moves_to_done(self, vault: Path):
        f = vault / "Needs_Action" / "task.md"
        f.write_text("done")
        dest = mark_done(f, vault)
        assert dest.parent.name == "Done"
        assert not f.exists()
