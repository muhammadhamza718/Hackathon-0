"""Unit tests for agents.frontmatter module."""

from __future__ import annotations

from agents.frontmatter import build, parse, update_field

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
