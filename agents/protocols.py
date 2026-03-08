"""Protocol definitions for agent system interfaces."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol, runtime_checkable


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


# ---------------------------------------------------------------------------
# Gold Tier Dependency Injection Protocols
# ---------------------------------------------------------------------------


@runtime_checkable
class OdooSessionProvider(Protocol):
    """Protocol for providing Odoo sessions (dependency injection)."""

    def get_session(self) -> Any:
        """Get an Odoo session object.

        Returns:
            An OdooSession or compatible session object.
        """
        ...


@runtime_checkable
class OdooRPCClientProtocol(Protocol):
    """Protocol for Odoo RPC client operations."""

    def search_read(
        self, model: str, domain: list, fields: list, limit: int = 100
    ) -> list[dict]:
        """Execute search_read on an Odoo model."""
        ...

    def read(self, model: str, ids: list[int], fields: list) -> list[dict]:
        """Read specific records by ID."""
        ...


@runtime_checkable
class PlatformAdapter(Protocol):
    """Protocol for social media platform adapters."""

    platform_name: str
    max_text_length: int
    max_images: int

    def adapt_content(self, content: str) -> str:
        """Adapt content for the specific platform."""
        ...


@runtime_checkable
class SocialBridgeProtocol(Protocol):
    """Protocol for social media bridge operations."""

    vault_root: Path

    def draft_post(
        self,
        platform: str,
        content: str,
        media_paths: tuple[str, ...] = (),
        scheduled: str = "immediate",
        rationale: str = "",
    ) -> Any:
        """Create a social media draft."""
        ...

    def draft_multi_post(
        self,
        content: str,
        platforms: list[str],
        media_paths: tuple[str, ...] = (),
        scheduled: str = "immediate",
        rationale: str = "",
    ) -> list[Any]:
        """Create drafts for multiple platforms."""
        ...

    def publish_approved(self, draft: Any) -> Any:
        """Publish an approved social post."""
        ...

    def get_engagement_summary(
        self, platform: str, period_days: int = 7
    ) -> dict:
        """Get engagement metrics for a platform."""
        ...


@runtime_checkable
class BriefingDataProvider(Protocol):
    """Protocol for providing briefing data (dependency injection)."""

    def get_revenue_data(self) -> tuple[float | None, list[str]]:
        """Get revenue data and unavailable sources."""
        ...

    def get_bottleneck_tasks(self) -> list[Any]:
        """Get bottleneck tasks."""
        ...

    def get_subscription_findings(self) -> list[Any]:
        """Get subscription audit findings."""
        ...
