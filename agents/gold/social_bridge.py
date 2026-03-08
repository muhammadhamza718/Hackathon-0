"""Multi-platform social media bridge via Browser MCP.

ALL social posts MUST go through ``/Pending_Approval/`` per Constitution XII.
Platform adapters handle content adaptation for Twitter/X, Facebook, and
Instagram with hashtag suggestions, emoji optimization, and character counting.
"""

from __future__ import annotations

import re
import unicodedata
import uuid
from dataclasses import dataclass, field
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
from agents.gold.image_optimizer import (
    OptimizationResult,
    optimize_image,
    validate_and_optimize_images,
    validate_image,
)
from agents.gold.models import PublishResult, SocialDraft
from agents.utils import ensure_dir, slugify, utcnow_iso


# ---------------------------------------------------------------------------
# Platform limits
# ---------------------------------------------------------------------------

PLATFORM_LIMITS: dict[str, dict] = {
    "X": {"max_text": 280, "max_images": 4, "hashtag_limit": 3},
    "Facebook": {"max_text": 63206, "max_images": 10, "hashtag_limit": 10},
    "Instagram": {"max_text": 2200, "max_images": 10, "hashtag_limit": 30},
}


# ---------------------------------------------------------------------------
# Hashtag suggestion engine
# ---------------------------------------------------------------------------

HASHTAG_CATEGORIES: dict[str, list[str]] = {
    "tech": ["#Tech", "#Innovation", "#AI", "#Automation", "#DigitalTransformation", "#MachineLearning"],
    "business": ["#Business", "#Entrepreneurship", "#Startup", "#Growth", "#Leadership", "#Strategy"],
    "marketing": ["#Marketing", "#SocialMedia", "#ContentMarketing", "#Brand", "#DigitalMarketing", "#SEO"],
    "productivity": ["#Productivity", "#TimeManagement", "#Efficiency", "#Workflow", "#Organization"],
    "finance": ["#Finance", "#Accounting", "#FinTech", "#Investment", "#Money", "#Budgeting"],
    "general": ["#Monday", "#Tuesday", "#Wednesday", "#Thursday", "#Friday", "#Weekend", "#Motivation"],
}

TRENDING_HASHTAGS: list[str] = [
    "#MondayMotivation", "#TuesdayThoughts", "#WednesdayWisdom",
    "#ThursdayThoughts", "#FridayFeeling", "#SaturdayVibes", "#SundayFunday",
    "#ThrowbackThursday", "#FlashbackFriday", "#NewWeekNewGoals",
]


def suggest_hashtags(
    content: str,
    category: str = "general",
    max_count: int = 5,
    include_trending: bool = False,
) -> list[str]:
    """Suggest relevant hashtags based on content and category.

    Args:
        content: The post content to analyze for keyword matching.
        category: Hashtag category (tech, business, marketing, etc.).
        max_count: Maximum number of hashtags to suggest.
        include_trending: Whether to include trending hashtags.

    Returns:
        List of suggested hashtags.
    """
    suggestions: list[str] = []
    content_lower = content.lower()

    # Get category hashtags
    category_tags = HASHTAG_CATEGORIES.get(category, HASHTAG_CATEGORIES["general"])

    # Keyword matching for smarter suggestions
    keyword_map = {
        "ai": ["#AI", "#ArtificialIntelligence", "#MachineLearning"],
        "automation": ["#Automation", "#RPA", "#WorkflowAutomation"],
        "business": ["#Business", "#Entrepreneurship", "#Startup"],
        "marketing": ["#Marketing", "#SocialMedia", "#ContentMarketing"],
        "productivity": ["#Productivity", "#Efficiency", "#TimeManagement"],
        "finance": ["#Finance", "#Accounting", "#FinTech"],
        "tech": ["#Tech", "#Technology", "#Innovation"],
    }

    for keyword, tags in keyword_map.items():
        if keyword in content_lower:
            suggestions.extend(tags[:2])

    # Add category tags
    suggestions.extend(category_tags[:max_count - len(suggestions)])

    # Add trending if requested
    if include_trending:
        day_name = datetime.now().strftime("%A")
        day_trending = [t for t in TRENDING_HASHTAGS if day_name[:3] in t]
        suggestions.extend(day_trending[:2])

    # Remove duplicates while preserving order
    seen: set[str] = set()
    unique: list[str] = []
    for tag in suggestions:
        if tag not in seen:
            seen.add(tag)
            unique.append(tag)

    return unique[:max_count]


# ---------------------------------------------------------------------------
# Emoji optimization
# ---------------------------------------------------------------------------

EMOJI_CATEGORIES: dict[str, list[str]] = {
    "celebration": ["🎉", "🎊", "🥳", "🍾", "✨", "🌟"],
    "business": ["💼", "📊", "📈", "💰", "🏢", "🤝"],
    "tech": ["💻", "🤖", "⚡", "🔧", "🔌", "💡"],
    "marketing": ["📣", "📢", "🎯", "📱", "👀", "🔥"],
    "positive": ["👍", "✅", "🌟", "💪", "🙌", "😊"],
    "negative": ["⚠️", "❌", "🚫", "😕", "📉", "⛔"],
    "neutral": ["ℹ️", "📌", "📝", "🔗", "📋", "🗓️"],
    "time": ["⏰", "📅", "⏱️", "🕐", "📆", "⌛"],
}

# Platform-specific emoji preferences (some platforms render differently)
PLATFORM_EMOJI_PREFERENCES: dict[str, dict[str, str]] = {
    "X": {
        "preferred": ["🔥", "💡", "⚡", "🚀", "📊"],
        "avoid": ["👨‍👩‍👧‍👦", "🧑‍🤝‍🧑"],  # Complex emojis may not render well
    },
    "Facebook": {
        "preferred": ["😊", "👍", "❤️", "🎉", "🙌"],
        "avoid": [],  # Facebook handles most emojis well
    },
    "Instagram": {
        "preferred": ["✨", "🌟", "💫", "🔥", "💕", "📸"],
        "avoid": [],  # Instagram is emoji-friendly
    },
}


def count_emoji_characters(text: str) -> int:
    """Count emoji characters in text (handles multi-codepoint emojis).

    Uses Unicode property checks and known emoji ranges for accurate counting.

    Args:
        text: The text to analyze.

    Returns:
        Number of emoji characters.
    """
    emoji_count = 0
    for char in text:
        code = ord(char)
        # Common emoji Unicode ranges
        if (
            0x1F300 <= code <= 0x1F9FF  # Miscellaneous Symbols and Pictographs, Emoticons, etc.
            or 0x2600 <= code <= 0x26FF  # Miscellaneous Symbols
            or 0x2700 <= code <= 0x27BF  # Dingbats
            or 0x1FA00 <= code <= 0x1FAFF  # Chess, symbols
            or 0x1F600 <= code <= 0x1F64F  # Emoticons
            or 0x1F680 <= code <= 0x1F6FF  # Transport and Map
            or code in (0x200D,)  # Zero-width joiner (part of complex emojis)
        ):
            emoji_count += 1
        # Also try unicodedata name check as fallback
        else:
            try:
                name = unicodedata.name(char, "")
                if "EMOJI" in name or "SYMBOL" in name:
                    emoji_count += 1
            except ValueError:
                pass
    return emoji_count


def get_emoji_display_width(text: str) -> int:
    """Calculate display width considering emoji take ~2 char widths.

    Args:
        text: The text to measure.

    Returns:
        Approximate display width in characters.
    """
    emoji_count = count_emoji_characters(text)
    regular_chars = len(text) - emoji_count
    # Emojis typically display as 2 character widths
    return regular_chars + (emoji_count * 2)


def optimize_emojis_for_platform(
    content: str,
    platform: str,
    max_emojis: int = 5,
) -> str:
    """Optimize emoji selection for platform-specific rendering.

    Args:
        content: The content with emojis to optimize.
        platform: Target platform (X, Facebook, Instagram).
        max_emojis: Maximum number of emojis to keep.

    Returns:
        Content with optimized emoji selection.
    """
    preferences = PLATFORM_EMOJI_PREFERENCES.get(platform, {})
    preferred = preferences.get("preferred", [])
    avoid = preferences.get("avoid", [])

    # Extract emojis from content
    emojis_found: list[tuple[int, str]] = []
    for i, char in enumerate(content):
        try:
            name = unicodedata.name(char, "")
            if any(kw in name for kw in ["EMOJI", "SYMBOL", "DINGBAT"]):
                emojis_found.append((i, char))
        except ValueError:
            pass

    # Remove avoided emojis
    result = content
    for pos, emoji in reversed(emojis_found):
        if emoji in avoid:
            result = result[:pos] + result[pos + 1:]

    # Count remaining emojis
    remaining_emoji_count = count_emoji_characters(result)

    # If still too many, reduce to max
    if remaining_emoji_count > max_emojis:
        # Keep first max_emojis emojis
        emoji_positions = []
        for i, char in enumerate(result):
            try:
                name = unicodedata.name(char, "")
                if any(kw in name for kw in ["EMOJI", "SYMBOL", "DINGBAT"]):
                    emoji_positions.append(i)
            except ValueError:
                pass

        # Remove excess emojis from end
        for pos in reversed(emoji_positions[max_emojis:]):
            result = result[:pos] + result[pos + 1:]

    return result


# ---------------------------------------------------------------------------
# Platform-specific best practices
# ---------------------------------------------------------------------------

PLATFORM_BEST_PRACTICES: dict[str, dict] = {
    "X": {
        "optimal_length": (100, 260),
        "hashtag_strategy": "1-3 highly relevant hashtags",
        "emoji_strategy": "Use sparingly (1-3), prefer simple emojis",
        "posting_tips": [
            "Keep it concise and punchy",
            "Use threads for longer content",
            "Include visuals for higher engagement",
            "Tag relevant accounts with @",
        ],
        "engagement_boosters": ["Ask questions", "Use polls", "Share timely news"],
    },
    "Facebook": {
        "optimal_length": (50, 200),
        "hashtag_strategy": "3-5 hashtags, mix of broad and niche",
        "emoji_strategy": "Moderate use (3-5), friendly tone",
        "posting_tips": [
            "Longer posts perform well",
            "Include call-to-action",
            "Use high-quality images",
            "Tag pages and people",
        ],
        "engagement_boosters": ["Ask for opinions", "Share stories", "Post videos"],
    },
    "Instagram": {
        "optimal_length": (150, 500),
        "hashtag_strategy": "10-30 hashtags, mix of popular and niche",
        "emoji_strategy": "Heavy use encouraged (5-10), visual storytelling",
        "posting_tips": [
            "First comment for hashtags (optional)",
            "High-quality visuals essential",
            "Use Stories for engagement",
            "Tag locations and accounts",
        ],
        "engagement_boosters": ["Behind-the-scenes", "User-generated content", "Reels"],
    },
}


def get_platform_best_practices(platform: str) -> dict:
    """Get best practices for a specific platform.

    Args:
        platform: Platform name (X, Facebook, Instagram).

    Returns:
        Dictionary of best practices.

    Raises:
        SocialMediaError: If platform is unknown.
    """
    practices = PLATFORM_BEST_PRACTICES.get(platform)
    if practices is None:
        raise SocialMediaError(f"Unknown platform: {platform}")
    return practices


# ---------------------------------------------------------------------------
# Platform adapters
# ---------------------------------------------------------------------------


class PlatformAdapter(Protocol):
    """Protocol that each platform adapter must satisfy."""

    platform_name: str
    max_text_length: int
    max_images: int

    def adapt_content(self, content: str) -> str: ...
    def count_characters(self, content: str) -> int: ...
    def suggest_hashtags(self, content: str, max_count: int = 5) -> list[str]: ...


@dataclass
class TwitterAdapter:
    """Platform adapter for Twitter/X with character-aware counting."""

    platform_name: str = "X"
    max_text_length: int = 280
    max_images: int = 4
    hashtag_limit: int = 3

    def adapt_content(self, content: str) -> str:
        """Truncate to 280 chars for Twitter/X, preserving emoji integrity."""
        if len(content) <= self.max_text_length:
            return content

        # Try to truncate at word boundary, preserving emojis
        truncated = content[: self.max_text_length - 3]
        # Find last space or emoji boundary
        last_space = truncated.rfind(" ")
        if last_space > self.max_text_length - 50:
            truncated = truncated[:last_space]

        return truncated + "..."

    def count_characters(self, content: str) -> int:
        """Count characters with emoji awareness for X platform.

        X counts URLs as 23 chars regardless of length.
        Emojis count as 2 characters for display width.
        """
        url_pattern = r"https?://\S+"
        urls = re.findall(url_pattern, content)
        url_chars = sum(len(url) for url in urls)
        url_fixed = 23 * len(urls)

        emoji_count = count_emoji_characters(content)
        regular_chars = len(content) - emoji_count - url_chars

        return regular_chars + (emoji_count * 2) + url_fixed

    def suggest_hashtags(self, content: str, max_count: int = 5) -> list[str]:
        """Suggest hashtags optimized for X platform."""
        return suggest_hashtags(content, max_count=min(max_count, self.hashtag_limit))


@dataclass
class FacebookAdapter:
    """Platform adapter for Facebook with long-form support."""

    platform_name: str = "Facebook"
    max_text_length: int = 63206
    max_images: int = 10
    hashtag_limit: int = 10

    def adapt_content(self, content: str) -> str:
        """Facebook allows long content — pass through with minimal truncation."""
        if len(content) <= self.max_text_length:
            return content
        return content[: self.max_text_length - 3] + "..."

    def count_characters(self, content: str) -> int:
        """Count characters for Facebook (standard counting)."""
        return len(content)

    def suggest_hashtags(self, content: str, max_count: int = 5) -> list[str]:
        """Suggest hashtags optimized for Facebook."""
        return suggest_hashtags(
            content,
            max_count=min(max_count, self.hashtag_limit),
            include_trending=True,
        )


@dataclass
class InstagramAdapter:
    """Platform adapter for Instagram with hashtag optimization."""

    platform_name: str = "Instagram"
    max_text_length: int = 2200
    max_images: int = 10
    hashtag_limit: int = 30

    def adapt_content(self, content: str) -> str:
        """Truncate to 2200 chars, optimize for hashtag placement."""
        if len(content) <= self.max_text_length:
            return content

        # Try to preserve hashtags at the end
        hashtag_pattern = r"#\w+"
        hashtags = re.findall(hashtag_pattern, content)

        # Reserve space for hashtags
        hashtag_space = sum(len(h) + 1 for h in hashtags[:15])
        content_without_tags = re.sub(hashtag_pattern, "", content).strip()

        available = self.max_text_length - hashtag_space - 10
        truncated = content_without_tags[:available]

        return f"{truncated}\n\n{' '.join(hashtags[:15])}"

    def count_characters(self, content: str) -> int:
        """Count characters for Instagram (standard counting)."""
        return len(content)

    def suggest_hashtags(self, content: str, max_count: int = 5) -> list[str]:
        """Suggest hashtags optimized for Instagram (allows more)."""
        return suggest_hashtags(
            content,
            category="marketing",
            max_count=min(max_count, self.hashtag_limit),
            include_trending=True,
        )


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
        hashtag_category: str = "general",
        include_hashtags: bool = True,
        optimize_emojis: bool = True,
        optimize_images: bool = True,
        strip_exif: bool = True,
    ) -> SocialDraft:
        """Create a social media draft in ``/Pending_Approval/``.

        Args:
            platform: Target platform (X, Facebook, Instagram).
            content: Post content to adapt.
            media_paths: Paths to media files to attach.
            scheduled: Scheduling directive (immediate or specific time).
            rationale: Reason for creating this post.
            hashtag_category: Category for hashtag suggestions.
            include_hashtags: Whether to auto-suggest and append hashtags.
            optimize_emojis: Whether to optimize emojis for the platform.
            optimize_images: Whether to validate and optimize images.
            strip_exif: Whether to strip EXIF data from images for privacy.

        Returns:
            A ``SocialDraft`` with ``approval_status="pending"``.

        Raises:
            ContentValidationError: If content exceeds platform limits or
                images fail validation.
        """
        adapter = self._adapters.get(platform)
        if adapter is None:
            raise SocialMediaError(f"No adapter for platform: {platform}")

        # Optimize emojis if requested
        if optimize_emojis:
            content = optimize_emojis_for_platform(content, platform)

        # Validate content BEFORE adaptation
        self._validate_content(platform, content, media_paths)

        # Validate and optimize images if requested
        image_results: list[OptimizationResult] = []
        optimized_media_paths: list[str] = list(media_paths)

        if optimize_images and media_paths:
            for media_path in media_paths:
                # Validate each image
                validate_image(media_path, platform)
                # Optimize (may return same path if Pillow unavailable)
                result = optimize_image(
                    media_path,
                    platform,
                    strip_exif=strip_exif,
                )
                image_results.append(result)
                if result.optimized_path != result.original_path:
                    # Update path to optimized version
                    idx = optimized_media_paths.index(media_path)
                    optimized_media_paths[idx] = result.optimized_path

        # Auto-suggest hashtags if requested
        if include_hashtags:
            suggested = adapter.suggest_hashtags(content, max_count=10)
            # Append hashtags if not already present
            existing_hashtags = set(re.findall(r"#\w+", content))
            new_hashtags = [h for h in suggested if h not in existing_hashtags]
            if new_hashtags:
                hashtag_str = " ".join(new_hashtags[:5])  # Limit to 5 for draft
                content = f"{content}\n\n{hashtag_str}"

        adapted = adapter.adapt_content(content)

        # Calculate character count with emoji awareness
        char_count = adapter.count_characters(adapted)

        draft_id = str(uuid.uuid4())[:8]
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
        slug = slugify(f"social-post-{platform}")
        filename = f"{ts}_{slug}-{draft_id}.md"

        # Build approval file (Constitution XII format)
        media_section = "\n".join(
            f"- {p}" for p in optimized_media_paths
        ) if optimized_media_paths else "None"

        # Image optimization summary
        image_summary = ""
        if image_results:
            total_savings = sum(
                r.original_size_bytes - r.optimized_size_bytes
                for r in image_results
            )
            image_summary = (
                f"\n## Image Optimization\n\n"
                f"- **Images processed**: {len(image_results)}\n"
                f"- **Total size saved**: {total_savings / 1024:.1f} KB\n"
                f"- **EXIF stripped**: {strip_exif}\n"
            )

        # Get best practices for context
        best_practices = get_platform_best_practices(platform)

        file_content = (
            "---\n"
            f"type: social-post\n"
            f"platform: {platform}\n"
            f"scheduled: {scheduled}\n"
            f"rationale: {rationale}\n"
            f"risk_level: Low\n"
            f"character_count: {char_count}\n"
            f"emoji_optimized: {optimize_emojis}\n"
            f"images_optimized: {optimize_images}\n"
            "---\n\n"
            f"# Social Media Post Draft\n\n"
            f"**Platform**: {platform}\n"
            f"**Scheduled**: {scheduled}\n"
            f"**Character Count**: {char_count} (limit: {adapter.max_text_length})\n\n"
            f"## Content\n\n{adapted}\n\n"
            f"## Media\n\n{media_section}\n"
            f"{image_summary}"
            f"## Rationale\n\n{rationale}\n\n"
            f"## Platform Best Practices\n\n"
            f"- **Optimal Length**: {best_practices['optimal_length'][0]}-{best_practices['optimal_length'][1]} chars\n"
            f"- **Hashtag Strategy**: {best_practices['hashtag_strategy']}\n"
            f"- **Emoji Strategy**: {best_practices['emoji_strategy']}\n"
        )

        pending_dir = ensure_dir(self.vault_root / PENDING_APPROVAL_DIR)
        approval_path = pending_dir / filename
        approval_path.write_text(file_content, encoding="utf-8")

        draft = SocialDraft(
            draft_id=draft_id,
            platform=platform,
            content=adapted,
            media_paths=tuple(optimized_media_paths),
            scheduled=scheduled,
            rationale=rationale,
            approval_status="pending",
            approval_file_path=str(approval_path),
            adapted_versions={
                "character_count": char_count,
                "emoji_count": count_emoji_characters(adapted),
                "hashtag_count": len(re.findall(r"#\w+", adapted)),
                "image_optimizations": [
                    {
                        "original": r.original_path,
                        "optimized": r.optimized_path,
                        "compression_pct": r.compression_ratio,
                    }
                    for r in image_results
                ],
            },
        )

        append_gold_log(
            self.vault_root,
            action="social_draft",
            source_file=f"Pending_Approval/{filename}",
            details=f"Draft {platform} post ({char_count} chars, {len(image_results)} images optimized)",
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
        include_hashtags: bool = True,
        optimize_emojis: bool = True,
        optimize_images: bool = True,
        strip_exif: bool = True,
    ) -> list[SocialDraft]:
        """Adapt content for each platform and create separate drafts.

        Args:
            content: Original post content.
            platforms: List of target platforms.
            media_paths: Paths to media files to attach.
            scheduled: Scheduling directive.
            rationale: Reason for creating this post.
            include_hashtags: Whether to auto-suggest hashtags per platform.
            optimize_emojis: Whether to optimize emojis per platform.
            optimize_images: Whether to validate and optimize images.
            strip_exif: Whether to strip EXIF data from images.

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
                include_hashtags=include_hashtags,
                optimize_emojis=optimize_emojis,
                optimize_images=optimize_images,
                strip_exif=strip_exif,
            )
            drafts.append(draft)
        return drafts

    # ------------------------------------------------------------------
    # Utility methods
    # ------------------------------------------------------------------

    def get_hashtag_suggestions(
        self,
        content: str,
        platform: str,
        category: str = "general",
        max_count: int = 10,
    ) -> list[str]:
        """Get hashtag suggestions for content on a specific platform.

        Args:
            content: The post content to analyze.
            platform: Target platform (X, Facebook, Instagram).
            category: Hashtag category for suggestions.
            max_count: Maximum number of hashtags to suggest.

        Returns:
            List of suggested hashtags.

        Raises:
            SocialMediaError: If platform is unknown.
        """
        adapter = self._adapters.get(platform)
        if adapter is None:
            raise SocialMediaError(f"No adapter for platform: {platform}")
        return adapter.suggest_hashtags(content, max_count)

    def count_characters(
        self,
        content: str,
        platform: str,
    ) -> int:
        """Count characters with platform-aware emoji handling.

        Args:
            content: Content to count.
            platform: Target platform.

        Returns:
            Character count adjusted for platform rules.

        Raises:
            SocialMediaError: If platform is unknown.
        """
        adapter = self._adapters.get(platform)
        if adapter is None:
            raise SocialMediaError(f"No adapter for platform: {platform}")
        return adapter.count_characters(content)

    def get_best_practices(self, platform: str) -> dict:
        """Get platform-specific best practices.

        Args:
            platform: Target platform.

        Returns:
            Dictionary of best practices.
        """
        return get_platform_best_practices(platform)

    def analyze_content(
        self,
        content: str,
        platform: str,
    ) -> dict:
        """Analyze content for platform optimization.

        Args:
            content: Content to analyze.
            platform: Target platform.

        Returns:
            Analysis dict with character count, emoji count,
            hashtag count, and optimization suggestions.
        """
        adapter = self._adapters.get(platform)
        if adapter is None:
            raise SocialMediaError(f"No adapter for platform: {platform}")

        char_count = adapter.count_characters(content)
        emoji_count = count_emoji_characters(content)
        hashtag_count = len(re.findall(r"#\w+", content))
        best_practices = get_platform_best_practices(platform)

        suggestions: list[str] = []

        # Check length
        optimal = best_practices["optimal_length"]
        if char_count < optimal[0]:
            suggestions.append(f"Consider adding more content (current: {char_count}, optimal min: {optimal[0]})")
        elif char_count > optimal[1]:
            suggestions.append(f"Consider shortening (current: {char_count}, optimal max: {optimal[1]})")

        # Check emoji count
        emoji_strategy = best_practices["emoji_strategy"]
        if "sparingly" in emoji_strategy.lower() and emoji_count > 3:
            suggestions.append(f"Reduce emojis for {platform} (current: {emoji_count})")

        # Check hashtag count
        hashtag_limit = PLATFORM_LIMITS[platform]["hashtag_limit"]
        if hashtag_count > hashtag_limit:
            suggestions.append(f"Reduce hashtags (current: {hashtag_count}, limit: {hashtag_limit})")

        return {
            "platform": platform,
            "character_count": char_count,
            "character_limit": adapter.max_text_length,
            "emoji_count": emoji_count,
            "hashtag_count": hashtag_count,
            "within_limits": char_count <= adapter.max_text_length,
            "suggestions": suggestions,
        }

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
    # Engagement and Analytics (READ — autonomous)
    # ------------------------------------------------------------------

    def get_engagement_summary(
        self,
        platform: str,
        period_days: int = 7,
        compare_previous: bool = True,
    ) -> dict:
        """Retrieve engagement metrics for a platform with trend analysis.

        Args:
            platform: Target platform (X, Facebook, Instagram).
            period_days: Number of days for the analysis period.
            compare_previous: Whether to compare with previous period.

        Returns:
            Dict with engagement metrics and week-over-week changes.

        Note:
            In production this calls Browser MCP to navigate to analytics.
            Currently returns simulated data for testing.
        """
        # Simulated data — Browser MCP integration point
        current = {
            "X": {"posts": 12, "impressions": 45000, "likes": 890, "comments": 67, "shares": 123},
            "Facebook": {"posts": 8, "impressions": 32000, "likes": 1200, "comments": 145, "shares": 89},
            "Instagram": {"posts": 15, "impressions": 78000, "likes": 3400, "comments": 234, "shares": 156},
        }

        previous = {
            "X": {"posts": 10, "impressions": 38000, "likes": 720, "comments": 52, "shares": 98},
            "Facebook": {"posts": 7, "impressions": 28000, "likes": 980, "comments": 112, "shares": 67},
            "Instagram": {"posts": 12, "impressions": 65000, "likes": 2800, "comments": 189, "shares": 134},
        }

        current_data = current.get(platform, {})
        previous_data = previous.get(platform, {}) if compare_previous else {}

        # Calculate week-over-week changes
        wow_changes = {}
        for metric in ["posts", "impressions", "likes", "comments", "shares"]:
            curr_val = current_data.get(metric, 0)
            prev_val = previous_data.get(metric, 0) if previous_data else 0
            if prev_val > 0:
                change_pct = ((curr_val - prev_val) / prev_val) * 100
                trend = "up" if change_pct > 0 else ("down" if change_pct < 0 else "flat")
            else:
                change_pct = 0
                trend = "flat"
            wow_changes[metric] = {
                "current": curr_val,
                "previous": prev_val,
                "change_pct": round(change_pct, 1),
                "trend": trend,
            }

        # Calculate engagement rate
        total_engagement = (
            current_data.get("likes", 0)
            + current_data.get("comments", 0)
            + current_data.get("shares", 0)
        )
        impressions = current_data.get("impressions", 1)
        engagement_rate = (total_engagement / impressions) * 100 if impressions > 0 else 0

        return {
            "platform": platform,
            "period_days": period_days,
            "metrics": {
                "posts": wow_changes.get("posts", {}),
                "impressions": wow_changes.get("impressions", {}),
                "likes": wow_changes.get("likes", {}),
                "comments": wow_changes.get("comments", {}),
                "shares": wow_changes.get("shares", {}),
            },
            "engagement_rate": round(engagement_rate, 2),
            "total_engagement": total_engagement,
            "summary": self._generate_engagement_summary(platform, wow_changes, engagement_rate),
        }

    def _generate_engagement_summary(
        self,
        platform: str,
        wow_changes: dict,
        engagement_rate: float,
    ) -> str:
        """Generate human-readable engagement summary.

        Args:
            platform: Platform name.
            wow_changes: Week-over-week changes dict.
            engagement_rate: Current engagement rate percentage.

        Returns:
            Human-readable summary string.
        """
        highlights = []

        # Check impressions trend
        imp_trend = wow_changes.get("impressions", {}).get("trend", "flat")
        imp_change = wow_changes.get("impressions", {}).get("change_pct", 0)
        if imp_trend == "up":
            highlights.append(f"Impressions up {imp_change}%")
        elif imp_trend == "down":
            highlights.append(f"Impressions down {abs(imp_change)}%")

        # Check engagement rate
        if engagement_rate > 3:
            highlights.append(f"Strong engagement rate ({engagement_rate:.1f}%)")
        elif engagement_rate < 1:
            highlights.append("Engagement rate below average")

        # Check top metric
        top_growth = max(
            wow_changes.items(),
            key=lambda x: x[1].get("change_pct", 0),
            default=None,
        )
        if top_growth and top_growth[1].get("change_pct", 0) > 10:
            highlights.append(f"{top_growth[0].title()} leading growth")

        if not highlights:
            return f"{platform} performance stable this period."

        return f"{platform}: {'; '.join(highlights)}."

    def get_multi_platform_summary(
        self,
        platforms: list[str] | None = None,
        period_days: int = 7,
    ) -> dict:
        """Aggregate engagement metrics across multiple platforms.

        Args:
            platforms: List of platforms to include (default: all).
            period_days: Analysis period in days.

        Returns:
            Aggregated summary with per-platform and total metrics.
        """
        if platforms is None:
            platforms = ["X", "Facebook", "Instagram"]

        platform_summaries = {}
        total_impressions = 0
        total_engagement = 0

        for platform in platforms:
            summary = self.get_engagement_summary(platform, period_days)
            platform_summaries[platform] = summary
            total_impressions += summary["metrics"]["impressions"].get("current", 0)
            total_engagement += summary["total_engagement"]

        return {
            "period_days": period_days,
            "platforms": platform_summaries,
            "totals": {
                "impressions": total_impressions,
                "engagement": total_engagement,
                "engagement_rate": round(
                    (total_engagement / total_impressions * 100)
                    if total_impressions > 0 else 0,
                    2,
                ),
            },
            "top_platform": max(
                platform_summaries.items(),
                key=lambda x: x[1]["total_engagement"],
                default=(None, None),
            )[0],
        }

    def get_top_performing_posts(
        self,
        platform: str,
        period_days: int = 7,
        limit: int = 5,
    ) -> list[dict]:
        """Get top-performing posts for a platform.

        Args:
            platform: Target platform.
            period_days: Analysis period in days.
            limit: Maximum number of posts to return.

        Returns:
            List of top posts with engagement metrics.

        Note:
            In production, this would query actual post data via Browser MCP.
        """
        # Simulated top posts — Browser MCP integration point
        simulated_posts = {
            "X": [
                {"id": "post_1", "content": "AI automation tips...", "likes": 234, "shares": 45, "comments": 23},
                {"id": "post_2", "content": "New product launch...", "likes": 189, "shares": 67, "comments": 34},
            ],
            "Facebook": [
                {"id": "post_1", "content": "Behind the scenes...", "likes": 456, "shares": 23, "comments": 67},
                {"id": "post_2", "content": "Customer testimonial...", "likes": 345, "shares": 34, "comments": 45},
            ],
            "Instagram": [
                {"id": "post_1", "content": "Product showcase...", "likes": 890, "shares": 56, "comments": 78},
                {"id": "post_2", "content": "Team culture...", "likes": 756, "shares": 34, "comments": 89},
            ],
        }

        posts = simulated_posts.get(platform, [])

        # Calculate engagement score for each post
        for post in posts:
            post["engagement_score"] = (
                post["likes"] * 1
                + post["shares"] * 2
                + post["comments"] * 1.5
            )

        # Sort by engagement score and return top N
        sorted_posts = sorted(posts, key=lambda x: x["engagement_score"], reverse=True)
        return sorted_posts[:limit]

    def generate_analytics_report(
        self,
        platforms: list[str] | None = None,
        period_days: int = 7,
        include_top_posts: bool = True,
    ) -> str:
        """Generate comprehensive analytics report in markdown format.

        Args:
            platforms: Platforms to include (default: all).
            period_days: Analysis period in days.
            include_top_posts: Whether to include top-performing posts.

        Returns:
            Markdown-formatted analytics report.
        """
        if platforms is None:
            platforms = ["X", "Facebook", "Instagram"]

        multi_summary = self.get_multi_platform_summary(platforms, period_days)

        report = [
            "# Social Media Analytics Report",
            f"\n**Period**: Last {period_days} days",
            f"\n**Generated**: {utcnow_iso()}",
            "\n## Executive Summary",
            f"\n- **Total Impressions**: {multi_summary['totals']['impressions']:,}",
            f"- **Total Engagement**: {multi_summary['totals']['engagement']:,}",
            f"- **Overall Engagement Rate**: {multi_summary['totals']['engagement_rate']}%",
            f"- **Top Platform**: {multi_summary['top_platform']}",
        ]

        report.append("\n## Platform Breakdown\n")

        for platform in platforms:
            summary = multi_summary["platforms"].get(platform, {})
            if not summary:
                continue

            metrics = summary.get("metrics", {})
            report.append(f"\n### {platform}\n")
            report.append(f"- **Impressions**: {metrics.get('impressions', {}).get('current', 0):,} "
                         f"({metrics.get('impressions', {}).get('change_pct', 0):+.1f}%)")
            report.append(f"- **Likes**: {metrics.get('likes', {}).get('current', 0):,} "
                         f"({metrics.get('likes', {}).get('change_pct', 0):+.1f}%)")
            report.append(f"- **Comments**: {metrics.get('comments', {}).get('current', 0):,} "
                         f"({metrics.get('comments', {}).get('change_pct', 0):+.1f}%)")
            report.append(f"- **Shares**: {metrics.get('shares', {}).get('current', 0):,} "
                         f"({metrics.get('shares', {}).get('change_pct', 0):+.1f}%)")
            report.append(f"- **Engagement Rate**: {summary.get('engagement_rate', 0)}%")
            report.append(f"- **Summary**: {summary.get('summary', 'N/A')}")

        if include_top_posts:
            report.append("\n## Top Performing Posts\n")
            for platform in platforms:
                top_posts = self.get_top_performing_posts(platform, period_days, limit=3)
                if top_posts:
                    report.append(f"\n### {platform}\n")
                    for i, post in enumerate(top_posts, 1):
                        report.append(f"{i}. {post.get('content', 'N/A')[:50]}...")
                        report.append(
                            f"   - Likes: {post.get('likes', 0)}, "
                            f"Shares: {post.get('shares', 0)}, "
                            f"Comments: {post.get('comments', 0)}"
                        )

        return "\n".join(report)
