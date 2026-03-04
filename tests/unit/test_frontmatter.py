"""Unit tests for agents.frontmatter module."""

from __future__ import annotations

from agents.frontmatter import FrontmatterBuilder, build, parse, strip, update_field

SAMPLE = """---
title: My Task
priority: high
status: draft
---
# My Task

Description here.
"""


class TestParse:
    def test_extracts_fields(self):
        result = parse(SAMPLE)
        assert result["title"] == "My Task"
        assert result["priority"] == "high"
        assert result["status"] == "draft"

    def test_empty_content(self):
        assert parse("no frontmatter") == {}

    def test_no_frontmatter_delimiters(self):
        assert parse("just text\nmore text") == {}


class TestUpdateField:
    def test_updates_existing(self):
        result = update_field(SAMPLE, "status", "active")
        assert "status: active" in result
        assert "status: draft" not in result

    def test_preserves_other_fields(self):
        result = update_field(SAMPLE, "status", "active")
        assert "title: My Task" in result
        assert "priority: high" in result


class TestBuild:
    def test_creates_frontmatter(self):
        result = build({"title": "Test", "status": "draft"})
        assert result.startswith("---")
        assert result.endswith("---")
        assert "title: Test" in result

    def test_multiple_fields(self):
        result = build({"a": "1", "b": "2", "c": "3"})
        assert "a: 1" in result
        assert "b: 2" in result
        assert "c: 3" in result


class TestStrip:
    def test_removes_frontmatter(self):
        result = strip(SAMPLE)
        assert "---" not in result
        assert result.startswith("# My Task")

    def test_no_frontmatter_returns_content(self):
        assert strip("plain text") == "plain text"


class TestFrontmatterBuilder:
    """Verify fluent builder pattern for frontmatter construction."""

    def test_set_and_build(self):
        fm = FrontmatterBuilder().set("title", "Test").set("status", "active").build()
        assert "title: Test" in fm
        assert "status: active" in fm
        assert fm.startswith("---")

    def test_chaining_returns_same_instance(self):
        builder = FrontmatterBuilder()
        result = builder.set("a", "1")
        assert result is builder

    def test_remove_field(self):
        builder = FrontmatterBuilder().set("a", "1").set("b", "2").remove("a")
        fields = builder.to_dict()
        assert "a" not in fields
        assert "b" in fields

    def test_remove_nonexistent_no_error(self):
        builder = FrontmatterBuilder().remove("ghost")
        assert builder.to_dict() == {}

    def test_to_dict_returns_copy(self):
        builder = FrontmatterBuilder().set("x", "1")
        d = builder.to_dict()
        d["x"] = "mutated"
        assert builder.to_dict()["x"] == "1"

    def test_build_output_matches_build_function(self):
        fields = {"task_id": "PLAN-001", "status": "draft"}
        builder_output = FrontmatterBuilder().set("task_id", "PLAN-001").set("status", "draft").build()
        function_output = build(fields)
        assert builder_output == function_output
