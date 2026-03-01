"""Unit tests for sentinel.events module."""

from __future__ import annotations

from pathlib import Path

from sentinel.events import EventType, FileEvent


class TestEventType:
    def test_created_value(self):
        assert EventType.CREATED.value == "created"

    def test_all_types(self):
        assert len(EventType) == 4


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
        try:
            e.event_type = EventType.DELETED  # type: ignore
            assert False, "Should be frozen"
        except AttributeError:
            pass

    def test_moved_event_with_dest(self):
        e = FileEvent(EventType.MOVED, Path("a.md"), dest_path=Path("b.md"))
        assert e.dest_path == Path("b.md")
