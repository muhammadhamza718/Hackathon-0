"""Unit tests for sentinel.events module."""

from __future__ import annotations

from pathlib import Path

import pytest

from sentinel.events import EventType, FileEvent


class TestEventType:
    def test_created_value(self):
        assert EventType.CREATED.value == "created"

    def test_all_types(self):
        assert len(EventType) == 4

    @pytest.mark.parametrize(
        "event_type,expected",
        [
            (EventType.CREATED, False),
            (EventType.MODIFIED, False),
            (EventType.DELETED, True),
            (EventType.MOVED, False),
        ],
    )
    def test_is_destructive(self, event_type: EventType, expected: bool):
        assert event_type.is_destructive is expected

    @pytest.mark.parametrize(
        "event_type,expected",
        [
            (EventType.CREATED, True),
            (EventType.MODIFIED, True),
            (EventType.DELETED, False),
            (EventType.MOVED, False),
        ],
    )
    def test_requires_content_read(self, event_type: EventType, expected: bool):
        assert event_type.requires_content_read is expected


class TestFileEvent:
    def test_filename(self):
        e = FileEvent(EventType.CREATED, Path("/vault/Inbox/task.md"))
        assert e.filename == "task.md"

    def test_extension(self):
        e = FileEvent(EventType.CREATED, Path("/vault/Inbox/task.md"))
        assert e.extension == ".md"

    def test_is_markdown(self):
        e = FileEvent(EventType.CREATED, Path("task.md"))
        assert e.is_markdown is True

    def test_not_markdown(self):
        e = FileEvent(EventType.CREATED, Path("image.png"))
        assert e.is_markdown is False

    def test_str_representation(self):
        e = FileEvent(EventType.CREATED, Path("task.md"))
        s = str(e)
        assert "created" in s
        assert "task.md" in s

    def test_frozen(self):
        e = FileEvent(EventType.CREATED, Path("task.md"))
        with pytest.raises(AttributeError):
            e.event_type = EventType.DELETED  # type: ignore[misc]

    def test_moved_event_with_dest(self):
        e = FileEvent(EventType.MOVED, Path("a.md"), dest_path=Path("b.md"))
        assert e.dest_path == Path("b.md")

    def test_has_timestamp(self):
        e = FileEvent(EventType.CREATED, Path("task.md"))
        assert e.timestamp is not None

    def test_default_dest_path_none(self):
        e = FileEvent(EventType.CREATED, Path("task.md"))
        assert e.dest_path is None
