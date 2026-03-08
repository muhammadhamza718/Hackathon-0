"""Multi-platform social media bridge via Browser MCP.

ALL social posts MUST go through ``/Pending_Approval/`` per Constitution XII.
Platform adapters handle content adaptation for Twitter/X, Facebook, and
Instagram.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol

from agents.constants import (
    APPROVED_DIR,
    DONE_DIR,
    PENDING_APPROVAL_DIR,
)
from agents.exceptions import (
    ApprovalNotFoundError,
    ContentValidationError,
    SocialMediaError,
)
from agents.gold.audit_gold import append_gold_log
from agents.gold.models import PublishResult, SocialDraft
from agents.utils import ensure_dir, slugify, utcnow_iso


# ---------------------------------------------------------------------------
# Platform limits
# ---------------------------------------------------------------------------

PLATFORM_LIMITS: dict[str, dict] = {
    "X": {"max_text": 280, "max_images": 4},
    "Facebook": {"max_text": 63206, "max_images": 10},
    "Instagram": {"max_text": 2200, "max_images": 10},
}


# ---------------------------------------------------------------------------
# Platform adapters
# ---------------------------------------------------------------------------


class PlatformAdapter(Protocol):
    """Protocol that each platform adapter must satisfy."""

    platform_name: str
    max_text_length: int
    max_images: int

    def adapt_content(self, content: str) -> str: ...


@dataclass
class TwitterAdapter:
    platform_name: str = "X"
    max_text_length: int = 280
    max_images: int = 4

    def adapt_content(self, content: str) -> str:
        """Truncate to 280 chars for Twitter/X."""
        if len(content) <= self.max_text_length:
            return content
        return content[: self.max_text_length - 3] + "..."


@dataclass
class FacebookAdapter:
    platform_name: str = "Facebook"
    max_text_length: int = 63206
    max_images: int = 10

    def adapt_content(self, content: str) -> str:
        """Facebook allows long content — pass through."""
        return content[: self.max_text_length]


@dataclass
class InstagramAdapter:
    platform_name: str = "Instagram"
    max_text_length: int = 2200
    max_images: int = 10

    def adapt_content(self, content: str) -> str:
        """Truncate to 2200 chars, optimize for hashtags."""
        return content[: self.max_text_length]


_DEFAULT_ADAPTERS: dict[str, PlatformAdapter] = {
    "X": TwitterAdapter(),
    "Facebook": FacebookAdapter(),
    "Instagram": InstagramAdapter(),
}


# ---------------------------------------------------------------------------
# Social Bridge
# ---------------------------------------------------------------------------


class SocialBridge:
    """Multi-platform social media management with HITL approval gating.

    Supports dependency injection for platform adapters, enabling custom
    platform implementations and easier testing.
    """

    def __init__(
        self,
        vault_root: Path,
        adapters: dict[str, PlatformAdapter] | None = None,
    ) -> None:
        """Initialize SocialBridge.

        Args:
            vault_root: Root path of the vault.
            adapters: Optional dict of platform name to PlatformAdapter.
                     If not provided, uses default adapters for X, Facebook,
                     and Instagram.
        """
        self.vault_root = vault_root
        self._adapters = adapters or dict(_DEFAULT_ADAPTERS)

    def _validate_content(
        self, platform: str, content: str, media_paths: tuple[str, ...]
    ) -> None:
        """Raise ``ContentValidationError`` if content exceeds limits."""
        limits = PLATFORM_LIMITS.get(platform)
        if limits is None:
            raise ContentValidationError(f"Unknown platform: {platform}")
        if len(content) > limits["max_text"]:
            raise ContentValidationError(
                f"Content exceeds {platform} limit of {limits['max_text']} chars "
                f"(got {len(content)})"
            )
        if len(media_paths) > limits["max_images"]:
            raise ContentValidationError(
                f"Too many images for {platform}: max {limits['max_images']}, "
                f"got {len(media_paths)}"
            )

    # ------------------------------------------------------------------
    # Draft (always to /Pending_Approval/)
    # ------------------------------------------------------------------

    def draft_post(
        self,
        platform: str,
        content: str,
        media_paths: tuple[str, ...] = (),
        scheduled: str = "immediate",
        rationale: str = "",
    ) -> SocialDraft:
        """Create a social media draft in ``/Pending_Approval/``.

        Returns:
            A ``SocialDraft`` with ``approval_status="pending"``.

        Raises:
            ContentValidationError: If content exceeds platform limits.
        """
        adapter = self._adapters.get(platform)
        if adapter is None:
            raise SocialMediaError(f"No adapter for platform: {platform}")

        # Validate BEFORE adaptation
        self._validate_content(platform, content, media_paths)

        adapted = adapter.adapt_content(content)

        draft_id = str(uuid.uuid4())[:8]
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
        slug = slugify(f"social-post-{platform}")
        filename = f"{ts}_{slug}-{draft_id}.md"

        # Build approval file (Constitution XII format)
        media_section = "\n".join(
            f"- {p}" for p in media_paths
        ) if media_paths else "None"

        file_content = (
            "---\n"
            f"type: social-post\n"
            f"platform: {platform}\n"
            f"scheduled: {scheduled}\n"
            f"rationale: {rationale}\n"
            f"risk_level: Low\n"
            "---\n\n"
            f"# Social Media Post Draft\n\n"
            f"**Platform**: {platform}\n"
            f"**Scheduled**: {scheduled}\n\n"
            f"## Content\n\n{adapted}\n\n"
            f"## Media\n\n{media_section}\n\n"
            f"## Rationale\n\n{rationale}\n"
        )

        pending_dir = ensure_dir(self.vault_root / PENDING_APPROVAL_DIR)
        approval_path = pending_dir / filename
        approval_path.write_text(file_content, encoding="utf-8")

        draft = SocialDraft(
            draft_id=draft_id,
            platform=platform,
            content=adapted,
            media_paths=media_paths,
            scheduled=scheduled,
            rationale=rationale,
            approval_status="pending",
            approval_file_path=str(approval_path),
        )

        append_gold_log(
            self.vault_root,
            action="social_draft",
            source_file=f"Pending_Approval/{filename}",
            details=f"Draft {platform} post ({len(adapted)} chars)",
            rationale=rationale or "Social media post draft",
        )

        return draft

    def draft_multi_post(
        self,
        content: str,
        platforms: list[str],
        media_paths: tuple[str, ...] = (),
        scheduled: str = "immediate",
        rationale: str = "",
    ) -> list[SocialDraft]:
        """Adapt content for each platform and create separate drafts.

        Returns:
            List of ``SocialDraft`` objects, one per platform.
        """
        drafts: list[SocialDraft] = []
        for platform in platforms:
            draft = self.draft_post(
                platform=platform,
                content=content,
                media_paths=media_paths,
                scheduled=scheduled,
                rationale=rationale,
            )
            drafts.append(draft)
        return drafts

    # ------------------------------------------------------------------
    # Publish (requires /Approved/)
    # ------------------------------------------------------------------

    def publish_approved(self, draft: SocialDraft) -> PublishResult:
        """Publish a previously approved social post.

        Checks ``/Approved/`` for the approval file, then executes via
        Browser MCP (or mock for testing).

        Raises:
            ApprovalNotFoundError: If the file is not in ``/Approved/``.
        """
        approved_dir = self.vault_root / APPROVED_DIR
        # Find approval file by draft_id
        matches = [
            f for f in approved_dir.iterdir()
            if f.is_file() and draft.draft_id in f.name
        ]

        if not matches:
            raise ApprovalNotFoundError(
                f"No approved file found for draft {draft.draft_id}"
            )

        # In production: execute via Browser MCP
        # For now: mark as published and move file to Done
        done_dir = ensure_dir(self.vault_root / DONE_DIR)
        for match in matches:
            match.rename(done_dir / match.name)

        result = PublishResult(
            success=True,
            platform=draft.platform,
            published_at=utcnow_iso(),
        )

        append_gold_log(
            self.vault_root,
            action="social_post",
            source_file=f"Done/{matches[0].name}",
            details=f"Published to {draft.platform}",
            rationale=draft.rationale or "Social media publication",
        )

        return result

    # ------------------------------------------------------------------
    # Engagement (READ — autonomous)
    # ------------------------------------------------------------------

    def get_engagement_summary(
        self, platform: str, period_days: int = 7
    ) -> dict:
        """Retrieve engagement metrics for a platform.

        In production this calls Browser MCP to navigate to analytics.
        Returns a dict with summary metrics.
        """
        # Placeholder — Browser MCP integration point
        return {
            "platform": platform,
            "period_days": period_days,
            "total_posts": 0,
            "total_impressions": 0,
            "total_likes": 0,
            "total_comments": 0,
            "total_shares": 0,
        }
