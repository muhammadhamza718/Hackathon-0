"""Protocol definitions for agent system interfaces."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable


@runtime_checkable
class FileRouter(Protocol):
    """Interface for routing files between vault directories."""

    def route(self, file_path: Path, vault_root: Path) -> Path:
        """Route a file to the appropriate vault directory.

        Args:
            file_path: Source file to route.
            vault_root: Root of the vault.

        Returns:
            Destination path after routing.
        """
        ...


@runtime_checkable
class Classifier(Protocol):
    """Interface for classifying task content."""

    def classify(self, content: str) -> str:
        """Classify content and return a classification label.

        Args:
            content: Text content to classify.

        Returns:
            Classification label string.
        """
        ...


@runtime_checkable
class AuditWriter(Protocol):
    """Interface for writing audit log entries."""

    def log(self, action: str, detail: str, tier: str) -> Path:
        """Write an audit entry.

        Args:
            action: Action type identifier.
            detail: Human-readable description.
            tier: Agent tier performing the action.

        Returns:
            Path to the written log file.
        """
        ...
