"""Unit tests for Gold Tier social media bridge."""

import json
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from agents.constants import APPROVED_DIR, DONE_DIR, PENDING_APPROVAL_DIR
from agents.exceptions import ApprovalNotFoundError, ContentValidationError
from agents.gold.social_bridge import (
    FacebookAdapter,
    InstagramAdapter,
    SocialBridge,
    TwitterAdapter,
)


class TestPlatformAdapters:
    """Test platform-specific adapters."""

    def test_twitter_adapter_adapt_content_short(self):
        """Test Twitter adapter with content under limit."""
        adapter = TwitterAdapter()
        content = "Short content"

        result = adapter.adapt_content(content)

        assert result == "Short content"
        assert len(result) <= adapter.max_text_length

    def test_twitter_adapter_adapt_content_long(self):
        """Test Twitter adapter truncates long content."""
        adapter = TwitterAdapter()
        long_content = "A" * 500  # Much longer than 280 char limit

        result = adapter.adapt_content(long_content)

        assert len(result) == 280  # Should be truncated to limit
        assert result.endswith("...")

    def test_facebook_adapter_pass_through_long_content(self):
        """Test Facebook adapter allows long content."""
        adapter = FacebookAdapter()
        long_content = "A" * 50000  # Under the 63206 limit

        result = adapter.adapt_content(long_content)

        assert result == long_content[:adapter.max_text_length]

    def test_instagram_adapter_truncates_content(self):
        """Test Instagram adapter truncates content."""
        adapter = InstagramAdapter()
        long_content = "A" * 3000  # Over the 2200 limit

        result = adapter.adapt_content(long_content)

        assert len(result) == 2200  # Should be truncated to limit


class TestSocialBridgeInitialization:
    """Test SocialBridge initialization."""

    def test_initialization(self, tmp_path):
        """Test initializing SocialBridge with vault root."""
        bridge = SocialBridge(tmp_path)

        assert bridge.vault_root == tmp_path
        assert "X" in bridge._adapters
        assert "Facebook" in bridge._adapters
        assert "Instagram" in bridge._adapters

    def test_initialization_with_injected_adapters(self, tmp_path):
        """Test initializing SocialBridge with custom injected adapters."""
        # Create mock custom adapters
        mock_adapter = Mock()
        mock_adapter.platform_name = "CustomPlatform"
        mock_adapter.max_text_length = 500
        mock_adapter.max_images = 5
        mock_adapter.adapt_content.return_value = "Custom adapted content"

        custom_adapters = {"CustomPlatform": mock_adapter}
        bridge = SocialBridge(tmp_path, adapters=custom_adapters)

        assert "CustomPlatform" in bridge._adapters
        assert bridge._adapters["CustomPlatform"] is mock_adapter
        # Default adapters should not be present
        assert "X" not in bridge._adapters


class TestContentValidation:
    """Test content validation logic."""

    def test_validate_content_within_limits(self):
        """Test validation passes for content within limits."""
        bridge = SocialBridge(Path("."))

        # This should not raise an exception
        bridge._validate_content("X", "Short content", ("image.jpg",))

    def test_validate_content_exceeds_text_limit(self):
        """Test validation raises for content exceeding text limit."""
        bridge = SocialBridge(Path("."))
        long_content = "A" * 500  # Way over Twitter's 280 char limit

        with pytest.raises(ContentValidationError, match="exceeds X limit"):
            bridge._validate_content("X", long_content, ())

    def test_validate_content_too_many_images(self):
        """Test validation raises for too many images."""
        bridge = SocialBridge(Path("."))
        media_paths = tuple([f"img{i}.jpg" for i in range(10)])  # Twitter allows max 4

        with pytest.raises(ContentValidationError, match="Too many images for X"):
            bridge._validate_content("X", "content", media_paths)

    def test_validate_content_unknown_platform(self):
        """Test validation raises for unknown platform."""
        bridge = SocialBridge(Path("."))

        with pytest.raises(ContentValidationError, match="Unknown platform"):
            bridge._validate_content("UnknownPlatform", "content", ())


class TestDraftPost:
    """Test draft_post functionality."""

    def test_draft_post_creates_approval_file(self, tmp_path):
        """Test that draft_post creates an approval file in Pending_Approval."""
        bridge = SocialBridge(tmp_path)

        draft = bridge.draft_post(
            platform="X",
            content="Test post content",
            media_paths=("image1.jpg", "image2.png"),
            scheduled="2026-03-10T10:00:00",
            rationale="Testing social media draft"
        )

        # Check that approval file was created
        pending_dir = tmp_path / PENDING_APPROVAL_DIR
        approval_files = list(pending_dir.glob("*.md"))
        assert len(approval_files) == 1

        # Check file content
        content = approval_files[0].read_text()
        assert "type: social-post" in content
        assert "platform: X" in content
        assert "scheduled: 2026-03-10T10:00:00" in content
        assert "Test post content" in content
        assert "image1.jpg" in content
        assert "Testing social media draft" in content

        # Check draft object
        assert draft.platform == "X"
        assert draft.content == "Test post content"
        assert draft.approval_status == "pending"
        assert draft.media_paths == ("image1.jpg", "image2.png")

    def test_draft_post_validation_failure(self, tmp_path):
        """Test that draft_post validates content before creating file."""
        bridge = SocialBridge(tmp_path)
        # Use Facebook to avoid content adaptation that truncates for Twitter
        # Create content that exceeds Facebook's theoretical limit when validated
        long_content = "A" * 70000  # Way over any reasonable limit

        with pytest.raises(ContentValidationError):
            bridge.draft_post("Facebook", long_content)

    def test_draft_post_unknown_platform(self, tmp_path):
        """Test that draft_post raises for unknown platform."""
        bridge = SocialBridge(tmp_path)

        with pytest.raises(Exception, match="No adapter"):  # SocialMediaError
            bridge.draft_post("UnknownPlatform", "content")


class TestDraftMultiPost:
    """Test draft_multi_post functionality."""

    def test_draft_multi_post_creates_multiple_files(self, tmp_path):
        """Test that draft_multi_post creates separate files for each platform."""
        bridge = SocialBridge(tmp_path)

        drafts = bridge.draft_multi_post(
            content="Multi-platform content",
            platforms=["X", "Facebook"],
            media_paths=("shared.jpg",),
            rationale="Multi-platform test"
        )

        # Should create 2 draft files (one for each platform)
        pending_dir = tmp_path / PENDING_APPROVAL_DIR
        approval_files = list(pending_dir.glob("*.md"))
        assert len(approval_files) == 2

        # Check that we have drafts for both platforms
        platforms_found = []
        for draft in drafts:
            platforms_found.append(draft.platform)

        assert set(platforms_found) == {"X", "Facebook"}
        assert len(drafts) == 2


class TestPublishApproved:
    """Test publish_approved functionality."""

    def test_publish_approved_moves_file_to_done(self, tmp_path):
        """Test that publish_approved moves approved file to Done."""
        # Setup vault structure
        approved_dir = tmp_path / APPROVED_DIR
        approved_dir.mkdir()
        done_dir = tmp_path / DONE_DIR
        done_dir.mkdir()

        # Create an approved file (simulate approval)
        approved_file = approved_dir / "2026-03-06T10-00-00_social-post-X-abc123.md"
        approved_file.write_text("# Approved post")

        bridge = SocialBridge(tmp_path)

        # Create a draft that matches the approved file
        from agents.gold.models import SocialDraft
        draft = SocialDraft(
            draft_id="abc123",
            platform="X",
            content="Test content",
            rationale="Test rationale"
        )

        result = bridge.publish_approved(draft)

        # Check that file was moved to Done
        assert not approved_file.exists()
        done_files = list(done_dir.glob("*.md"))
        assert len(done_files) == 1

        # Check result
        assert result.success
        assert result.platform == "X"

    def test_publish_approved_missing_approval_raises(self, tmp_path):
        """Test that publish_approved raises if no approved file exists."""
        # Setup vault structure
        approved_dir = tmp_path / APPROVED_DIR
        approved_dir.mkdir()

        bridge = SocialBridge(tmp_path)

        from agents.gold.models import SocialDraft
        draft = SocialDraft(
            draft_id="nonexistent",
            platform="X",
            content="Test content"
        )

        with pytest.raises(ApprovalNotFoundError):
            bridge.publish_approved(draft)


class TestEngagementSummary:
    """Test engagement summary functionality."""

    def test_get_engagement_summary_returns_dict(self, tmp_path):
        """Test that get_engagement_summary returns expected structure."""
        bridge = SocialBridge(tmp_path)

        result = bridge.get_engagement_summary("X", period_days=7)

        assert isinstance(result, dict)
        assert result["platform"] == "X"
        assert result["period_days"] == 7
        assert "total_posts" in result
        assert "total_impressions" in result
        assert "total_likes" in result
        assert "total_comments" in result
        assert "total_shares" in result