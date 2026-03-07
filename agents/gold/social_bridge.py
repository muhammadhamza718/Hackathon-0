"""Social media bridge with platform adapters.

Provides a unified interface for cross-platform social media management
with platform-specific adapters for X (Twitter), Facebook, and Instagram.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from .config import PLATFORM_CHAR_LIMITS, SOCIAL_PLATFORMS
from .exceptions import SocialDraftError, SocialPublishError
from .models import PublishResult, SocialDraft

logger = logging.getLogger(__name__)


@dataclass
class PlatformAdapterConfig:
    """Configuration for a platform adapter."""

    platform: str
    char_limit: int
    hashtag_limit: int = 10
    mention_limit: int = 10
    media_types: tuple[str, ...] = ("image", "video")
    max_media_count: int = 4


class PlatformAdapter(ABC):
    """Abstract base class for platform adapters."""

    def __init__(self, config: PlatformAdapterConfig):
        """Initialize the platform adapter.

        Args:
            config: Platform-specific configuration.
        """
        self.config = config

    @abstractmethod
    def adapt_content(self, content: str) -> str:
        """Adapt content for the platform.

        Args:
            content: Original content.

        Returns:
            Platform-adapted content.
        """
        pass

    @abstractmethod
    def validate_content(self, content: str) -> tuple[bool, str]:
        """Validate content for the platform.

        Args:
            content: Content to validate.

        Returns:
            Tuple of (is_valid, error_message).
        """
        pass

    @abstractmethod
    def format_hashtags(self, hashtags: list[str]) -> str:
        """Format hashtags for the platform.

        Args:
            hashtags: List of hashtag strings.

        Returns:
            Formatted hashtag string.
        """
        pass

    @abstractmethod
    def format_mentions(self, mentions: list[str]) -> str:
        """Format mentions for the platform.

        Args:
            mentions: List of mention handles.

        Returns:
            Formatted mention string.
        """
        pass

    def truncate_content(self, content: str, suffix: str = "...") -> str:
        """Truncate content to fit platform limits.

        Args:
            content: Content to truncate.
            suffix: Suffix to add when truncating.

        Returns:
            Truncated content.
        """
        limit = self.config.char_limit - len(suffix)
        if len(content) <= limit:
            return content

        # Try to break at word boundary
        truncated = content[:limit]
        last_space = truncated.rfind(" ")
        if last_space > limit // 2:
            truncated = truncated[:last_space]

        return truncated + suffix


class XAdapter(PlatformAdapter):
    """Platform adapter for X (Twitter)."""

    def __init__(self):
        """Initialize X adapter."""
        super().__init__(
            PlatformAdapterConfig(
                platform="X",
                char_limit=280,
                hashtag_limit=10,
                mention_limit=10,
                media_types=("image", "video", "gif"),
                max_media_count=4,
            )
        )

    def adapt_content(self, content: str) -> str:
        """Adapt content for X."""
        return self.truncate_content(content)

    def validate_content(self, content: str) -> tuple[bool, str]:
        """Validate content for X."""
        if len(content) > self.config.char_limit:
            return False, f"Content exceeds {self.config.char_limit} characters"
        return True, ""

    def format_hashtags(self, hashtags: list[str]) -> str:
        """Format hashtags for X."""
        limited = hashtags[: self.config.hashtag_limit]
        return " ".join(f"#{h}" for h in limited)

    def format_mentions(self, mentions: list[str]) -> str:
        """Format mentions for X."""
        limited = mentions[: self.config.mention_limit]
        return " ".join(f"@{m}" for m in limited)


class FacebookAdapter(PlatformAdapter):
    """Platform adapter for Facebook."""

    def __init__(self):
        """Initialize Facebook adapter."""
        super().__init__(
            PlatformAdapterConfig(
                platform="Facebook",
                char_limit=63206,
                hashtag_limit=30,
                mention_limit=50,
                media_types=("image", "video"),
                max_media_count=10,
            )
        )

    def adapt_content(self, content: str) -> str:
        """Adapt content for Facebook."""
        # Facebook supports longer content, no adaptation needed
        return content

    def validate_content(self, content: str) -> tuple[bool, str]:
        """Validate content for Facebook."""
        if len(content) > self.config.char_limit:
            return False, f"Content exceeds {self.config.char_limit} characters"
        return True, ""

    def format_hashtags(self, hashtags: list[str]) -> str:
        """Format hashtags for Facebook."""
        limited = hashtags[: self.config.hashtag_limit]
        return " ".join(f"#{h}" for h in limited)

    def format_mentions(self, mentions: list[str]) -> str:
        """Format mentions for Facebook."""
        # Facebook uses different mention format
        limited = mentions[: self.config.mention_limit]
        return " ".join(f"@{m}" for m in limited)


class InstagramAdapter(PlatformAdapter):
    """Platform adapter for Instagram."""

    def __init__(self):
        """Initialize Instagram adapter."""
        super().__init__(
            PlatformAdapterConfig(
                platform="Instagram",
                char_limit=2200,
                hashtag_limit=30,
                mention_limit=20,
                media_types=("image", "video"),
                max_media_count=10,  # Carousel
            )
        )

    def adapt_content(self, content: str) -> str:
        """Adapt content for Instagram."""
        # Instagram prefers shorter captions with hashtags at end
        return self.truncate_content(content)

    def validate_content(self, content: str) -> tuple[bool, str]:
        """Validate content for Instagram."""
        if len(content) > self.config.char_limit:
            return False, f"Content exceeds {self.config.char_limit} characters"
        return True, ""

    def format_hashtags(self, hashtags: list[str]) -> str:
        """Format hashtags for Instagram."""
        limited = hashtags[: self.config.hashtag_limit]
        # Instagram: hashtags work best at the end
        return "\n\n" + " ".join(f"#{h}" for h in limited)

    def format_mentions(self, mentions: list[str]) -> str:
        """Format mentions for Instagram."""
        limited = mentions[: self.config.mention_limit]
        return " ".join(f"@{m}" for m in limited)


class SocialBridge:
    """Unified bridge for cross-platform social media management.

    Provides a single interface for creating and publishing content
    across multiple platforms with automatic platform adaptation.
    """

    def __init__(self):
        """Initialize the social bridge."""
        self._adapters: dict[str, PlatformAdapter] = {
            "X": XAdapter(),
            "Facebook": FacebookAdapter(),
            "Instagram": InstagramAdapter(),
        }

    def get_adapter(self, platform: str) -> PlatformAdapter:
        """Get the adapter for a platform.

        Args:
            platform: Platform name.

        Returns:
            The platform adapter.

        Raises:
            ValueError: If platform not supported.
        """
        if platform not in self._adapters:
            raise ValueError(f"Unsupported platform: {platform}")
        return self._adapters[platform]

    def create_draft(
        self,
        content: str,
        platforms: list[str] | None = None,
        media_paths: list[str] | None = None,
        hashtags: list[str] | None = None,
        mentions: list[str] | None = None,
        rationale: str = "",
    ) -> dict[str, SocialDraft]:
        """Create drafts for multiple platforms.

        Args:
            content: Base content.
            platforms: List of platforms (default: all).
            media_paths: Paths to media files.
            hashtags: List of hashtags.
            mentions: List of mentions.
            rationale: Reason for creating this post.

        Returns:
            Dictionary mapping platform names to drafts.
        """
        if platforms is None:
            platforms = list(self._adapters.keys())

        drafts: dict[str, SocialDraft] = {}
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")

        for platform in platforms:
            adapter = self.get_adapter(platform)

            # Adapt content
            adapted = adapter.adapt_content(content)

            # Add hashtags
            if hashtags:
                adapted += "\n\n" + adapter.format_hashtags(hashtags)

            # Add mentions
            if mentions:
                adapted = adapter.format_mentions(mentions) + "\n\n" + adapted

            # Validate
            is_valid, error = adapter.validate_content(adapted)
            if not is_valid:
                raise SocialDraftError(
                    f"Invalid content for {platform}: {error}"
                )

            draft_id = f"draft_{platform.lower()}_{timestamp}"
            drafts[platform] = SocialDraft(
                draft_id=draft_id,
                platform=platform,
                content=adapted,
                media_paths=tuple(media_paths or []),
                rationale=rationale,
            )

        return drafts

    def adapt_for_platform(
        self, content: str, platform: str
    ) -> str:
        """Adapt content for a specific platform.

        Args:
            content: Base content.
            platform: Target platform.

        Returns:
            Platform-adapted content.
        """
        adapter = self.get_adapter(platform)
        return adapter.adapt_content(content)

    def validate_for_platform(
        self, content: str, platform: str
    ) -> tuple[bool, str]:
        """Validate content for a specific platform.

        Args:
            content: Content to validate.
            platform: Target platform.

        Returns:
            Tuple of (is_valid, error_message).
        """
        adapter = self.get_adapter(platform)
        return adapter.validate_content(content)

    def get_supported_platforms(self) -> list[str]:
        """Get list of supported platforms.

        Returns:
            List of platform names.
        """
        return list(self._adapters.keys())

    def get_platform_limits(self) -> dict[str, dict[str, Any]]:
        """Get character and media limits for all platforms.

        Returns:
            Dictionary mapping platform names to limit info.
        """
        return {
            name: {
                "char_limit": adapter.config.char_limit,
                "hashtag_limit": adapter.config.hashtag_limit,
                "mention_limit": adapter.config.mention_limit,
                "max_media_count": adapter.config.max_media_count,
                "media_types": adapter.config.media_types,
            }
            for name, adapter in self._adapters.items()
        }

    def publish(
        self, draft: SocialDraft
    ) -> PublishResult:
        """Publish a draft (placeholder - requires API integration).

        Args:
            draft: The draft to publish.

        Returns:
            PublishResult with success status.
        """
        # This is a placeholder - actual implementation would
        # integrate with platform APIs
        logger.info(f"Publishing draft {draft.draft_id} to {draft.platform}")

        # Simulate publishing
        return PublishResult(
            success=True,
            platform=draft.platform,
            published_at=datetime.now(timezone.utc).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            ),
            post_url=f"https://{draft.platform.lower()}.com/post/{draft.draft_id}",
        )
