"""Unit tests for agents.protocols module."""

from __future__ import annotations

from pathlib import Path

from agents.protocols import AuditWriter, Classifier, FileRouter


class _MockRouter:
    def route(self, file_path: Path, vault_root: Path) -> Path:
        return vault_root / file_path.name


class _MockClassifier:
    def classify(self, content: str) -> str:
        return "simple"


class _MockAuditWriter:
    def log(self, action: str, detail: str, tier: str) -> Path:
        return Path("/logs/audit.md")


class TestFileRouterProtocol:
    def test_isinstance_check(self):
        assert isinstance(_MockRouter(), FileRouter)

    def test_non_conforming_fails(self):
        assert not isinstance(object(), FileRouter)


class TestClassifierProtocol:
    def test_isinstance_check(self):
        assert isinstance(_MockClassifier(), Classifier)

    def test_non_conforming_fails(self):
        assert not isinstance(object(), Classifier)


class TestAuditWriterProtocol:
    def test_isinstance_check(self):
        assert isinstance(_MockAuditWriter(), AuditWriter)

    def test_non_conforming_fails(self):
        assert not isinstance(object(), AuditWriter)
