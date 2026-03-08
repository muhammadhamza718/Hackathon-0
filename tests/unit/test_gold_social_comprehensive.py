"""Comprehensive tests for social media automation and image handling."""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest

from agents.exceptions import ContentValidationError, SocialMediaError
from agents.gold.image_optimizer import (
    IMAGE_FORMAT,
    ImageInfo,
    OptimizationResult,
    detect_image_format,
    get_image_dimensions,
    get_optimization_summary,
    has_exif_data,
    optimize_image,
    validate_image,
    PLATFORM_IMAGE_LIMITS,
)
from agents.gold.social_automation import (
    BrowserAction,
    BrowserStep,
    PostResult,
    SocialMediaAutomation,
    create_automation,
)


class TestBrowserAction:
    """Test BrowserAction enum."""

    def test_browser_action_values(self):
        """Test browser action enum values."""
        assert BrowserAction.NAVIGATE.value == "navigate"
        assert BrowserAction.CLICK.value == "click"
        assert BrowserAction.TYPE.value == "type"
        assert BrowserAction.UPLOAD.value == "upload"
        assert BrowserAction.SCREENSHOT.value == "screenshot"
        assert BrowserAction.WAIT.value == "wait"
        assert BrowserAction.EVALUATE.value == "evaluate"


class TestBrowserStep:
    """Test BrowserStep dataclass."""

    def test_browser_step_creation(self):
        """Test creating browser step."""
        step = BrowserStep(
            action=BrowserAction.CLICK,
            selector="#button",
            description="Click button",
        )

        assert step.action == BrowserAction.CLICK
        assert step.selector == "#button"
        assert step.description == "Click button"
        assert step.value == ""
        assert step.timeout == 5000


class TestPostResult:
    """Test PostResult dataclass."""

    def test_post_result_success(self):
        """Test successful post result."""
        result = PostResult(
            success=True,
            platform="X",
            post_url="https://twitter.com/user/status/123",
            timestamp="2026-03-08T10:00:00Z",
        )

        assert result.success
        assert result.platform == "X"
        assert result.error is None

    def test_post_result_failure(self):
        """Test failed post result."""
        result = PostResult(
            success=False,
            platform="Facebook",
            error="Login failed",
            timestamp="2026-03-08T10:00:00Z",
        )

        assert not result.success
        assert result.error == "Login failed"


class TestSocialMediaAutomation:
    """Test SocialMediaAutomation class."""

    def test_initialization(self):
        """Test automation initialization."""
        automation = SocialMediaAutomation()

        assert automation._browser is None
        assert automation._vault_root is None
        assert automation._sessions == {}

    def test_initialization_with_client(self):
        """Test initialization with browser client."""
        mock_client = Mock()
        vault_root = Path("/tmp/vault")

        automation = SocialMediaAutomation(
            browser_client=mock_client,
            vault_root=vault_root,
        )

        assert automation._browser is mock_client
        assert automation._vault_root == vault_root

    def test_set_browser_client(self):
        """Test setting browser client."""
        automation = SocialMediaAutomation()
        mock_client = Mock()

        automation.set_browser_client(mock_client)

        assert automation._browser is mock_client

    def test_create_automation_factory(self):
        """Test create_automation factory function."""
        mock_client = Mock()
        vault_root = Path("/tmp/vault")

        automation = create_automation(
            browser_client=mock_client,
            vault_root=vault_root,
        )

        assert isinstance(automation, SocialMediaAutomation)
        assert automation._browser is mock_client

    @pytest.mark.asyncio
    async def test_execute_steps_without_client(self):
        """Test executing steps without browser client raises error."""
        automation = SocialMediaAutomation()
        steps = [BrowserStep(action=BrowserAction.NAVIGATE, value="https://example.com")]

        with pytest.raises(SocialMediaError, match="Browser client not set"):
            await automation._execute_steps(steps)

    @pytest.mark.asyncio
    async def test_execute_steps_success(self):
        """Test successful step execution."""
        mock_client = AsyncMock()
        mock_client.navigate.return_value = {"success": True}
        mock_client.click.return_value = {"success": True}
        mock_client.wait.return_value = {"success": True}

        automation = SocialMediaAutomation(browser_client=mock_client)
        steps = [
            BrowserStep(action=BrowserAction.NAVIGATE, value="https://example.com"),
            BrowserStep(action=BrowserAction.WAIT, timeout=100),
        ]

        results = await automation._execute_steps(steps)

        assert len(results) == 2
        mock_client.navigate.assert_called_once()
        mock_client.wait.assert_called_once()

    def test_get_x_post_steps(self):
        """Test X post step generation."""
        automation = SocialMediaAutomation()
        steps = automation._get_x_post_steps(
            content="Test tweet",
            media_paths=("image1.jpg", "image2.png"),
        )

        assert len(steps) > 5
        assert any(s.action == BrowserAction.NAVIGATE and "twitter.com" in s.value for s in steps)
        assert any(s.action == BrowserAction.TYPE for s in steps)
        assert any(s.action == BrowserAction.CLICK and "tweetButton" in s.selector for s in steps)

    def test_get_facebook_post_steps(self):
        """Test Facebook post step generation."""
        automation = SocialMediaAutomation()
        steps = automation._get_facebook_post_steps(
            content="Test post",
            media_paths=("image.jpg",),
        )

        assert len(steps) > 4
        assert any(s.action == BrowserAction.NAVIGATE and "facebook.com" in s.value for s in steps)
        assert any(s.action == BrowserAction.TYPE for s in steps)

    def test_get_instagram_post_steps(self):
        """Test Instagram post step generation."""
        automation = SocialMediaAutomation()
        steps = automation._get_instagram_post_steps(
            content="Test caption #hashtag",
            media_paths=("image.jpg",),
        )

        assert len(steps) > 8
        assert any(s.action == BrowserAction.NAVIGATE and "instagram.com" in s.value for s in steps)
        assert any(s.action == BrowserAction.TYPE and "caption" in s.description.lower() for s in steps)

    @pytest.mark.asyncio
    async def test_post_to_x_success(self):
        """Test successful X post."""
        mock_client = AsyncMock()
        mock_client.navigate.return_value = {"success": True}
        mock_client.click.return_value = {"success": True}
        mock_client.type.return_value = {"success": True}
        mock_client.upload.return_value = {"success": True}
        mock_client.wait.return_value = {"success": True}
        mock_client.screenshot.return_value = {"path": "/tmp/screenshot.png"}

        automation = SocialMediaAutomation(browser_client=mock_client)

        result = await automation.post_to_x(
            content="Test tweet",
            media_paths=("image.jpg",),
        )

        assert result.success
        assert result.platform == "X"
        assert result.error is None

    @pytest.mark.asyncio
    async def test_post_to_x_failure(self):
        """Test failed X post."""
        mock_client = AsyncMock()
        mock_client.navigate.side_effect = Exception("Network error")

        automation = SocialMediaAutomation(browser_client=mock_client)

        result = await automation.post_to_x(content="Test")

        assert not result.success
        assert result.platform == "X"
        assert result.error is not None

    @pytest.mark.asyncio
    async def test_post_to_all(self):
        """Test posting to all platforms."""
        mock_client = AsyncMock()
        mock_client.navigate.return_value = {"success": True}
        mock_client.click.return_value = {"success": True}
        mock_client.type.return_value = {"success": True}
        mock_client.wait.return_value = {"success": True}

        automation = SocialMediaAutomation(browser_client=mock_client)

        results = await automation.post_to_all(
            content="Multi-platform post",
            platforms=["X", "Facebook"],
        )

        assert "X" in results
        assert "Facebook" in results
        assert all(isinstance(r, PostResult) for r in results.values())


class TestImageOptimizer:
    """Test image optimization functions."""

    def test_platform_image_limits_structure(self):
        """Test platform image limits structure."""
        assert "X" in PLATFORM_IMAGE_LIMITS
        assert "Facebook" in PLATFORM_IMAGE_LIMITS
        assert "Instagram" in PLATFORM_IMAGE_LIMITS

        for platform, limits in PLATFORM_IMAGE_LIMITS.items():
            assert "max_file_size_mb" in limits
            assert "max_width" in limits
            assert "max_height" in limits
            assert "supported_formats" in limits

    def test_platform_limits_x(self):
        """Test X platform limits."""
        limits = PLATFORM_IMAGE_LIMITS["X"]
        assert limits["max_file_size_mb"] == 5
        assert limits["max_width"] == 4096
        assert limits["max_height"] == 4096
        assert "JPEG" in limits["supported_formats"]

    def test_platform_limits_facebook(self):
        """Test Facebook platform limits."""
        limits = PLATFORM_IMAGE_LIMITS["Facebook"]
        assert limits["max_file_size_mb"] == 15
        assert limits["max_width"] == 2048

    def test_platform_limits_instagram(self):
        """Test Instagram platform limits."""
        limits = PLATFORM_IMAGE_LIMITS["Instagram"]
        assert limits["max_file_size_mb"] == 8
        assert limits["max_width"] == 1080
        assert "aspect_ratio_min" in limits
        assert "aspect_ratio_max" in limits

    def test_validate_image_unknown_platform(self):
        """Test validation with unknown platform."""
        with pytest.raises(SocialMediaError, match="Unknown platform"):
            validate_image("test.jpg", "UnknownPlatform")

    def test_validate_image_not_found(self, tmp_path):
        """Test validation with non-existent file."""
        with pytest.raises(ContentValidationError, match="not found"):
            validate_image(tmp_path / "nonexistent.jpg", "X")

    def test_optimization_result_structure(self):
        """Test OptimizationResult structure."""
        result = OptimizationResult(
            original_path="/path/original.jpg",
            optimized_path="/path/optimized.jpg",
            original_size_bytes=1000000,
            optimized_size_bytes=500000,
            compression_ratio=50.0,
            format_changed=False,
            exif_stripped=True,
            dimensions_changed=False,
            warnings=[],
        )

        assert result.compression_ratio == 50.0
        assert result.exif_stripped
        assert result.optimized_size_bytes < result.original_size_bytes

    def test_get_optimization_summary_empty(self):
        """Test optimization summary with no results."""
        summary = get_optimization_summary([])

        assert summary["total_images"] == 0
        assert summary["total_savings_mb"] == 0

    def test_get_optimization_summary(self):
        """Test optimization summary calculation."""
        results = [
            OptimizationResult(
                original_path="1.jpg",
                optimized_path="1_opt.jpg",
                original_size_bytes=1000000,
                optimized_size_bytes=500000,
                compression_ratio=50.0,
                format_changed=False,
                exif_stripped=True,
                dimensions_changed=False,
                warnings=[],
            ),
            OptimizationResult(
                original_path="2.jpg",
                optimized_path="2_opt.jpg",
                original_size_bytes=2000000,
                optimized_size_bytes=1000000,
                compression_ratio=50.0,
                format_changed=False,
                exif_stripped=False,
                dimensions_changed=False,
                warnings=[],
            ),
        ]

        summary = get_optimization_summary(results)

        assert summary["total_images"] == 2
        assert summary["exif_stripped_count"] == 1
        assert summary["average_compression_pct"] == 50.0


class TestImageFormatDetection:
    """Test image format detection."""

    def test_detect_format_jpeg(self, tmp_path):
        """Test JPEG format detection."""
        # Create minimal JPEG file
        jpeg_data = bytes([
            0xFF, 0xD8,  # SOI
            0xFF, 0xE0, 0x00, 0x10,  # APP0
        ]) + b'JFIF\x00' + b'\x00' * 20

        img_path = tmp_path / "test.jpg"
        img_path.write_bytes(jpeg_data)

        fmt = detect_image_format(img_path)
        assert fmt == "JPEG"

    def test_detect_format_png(self, tmp_path):
        """Test PNG format detection."""
        # Create minimal PNG file
        png_data = bytes([
            0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A,  # PNG signature
        ]) + b'\x00' * 20

        img_path = tmp_path / "test.png"
        img_path.write_bytes(png_data)

        fmt = detect_image_format(img_path)
        assert fmt == "PNG"

    def test_detect_format_gif(self, tmp_path):
        """Test GIF format detection."""
        gif_data = b"GIF89a" + b'\x00' * 20

        img_path = tmp_path / "test.gif"
        img_path.write_bytes(gif_data)

        fmt = detect_image_format(img_path)
        assert fmt == "GIF"

    def test_detect_format_webp(self, tmp_path):
        """Test WEBP format detection."""
        webp_data = b"RIFF" + b"\x00" * 4 + b"WEBP" + b'\x00' * 20

        img_path = tmp_path / "test.webp"
        img_path.write_bytes(webp_data)

        fmt = detect_image_format(img_path)
        assert fmt == "WEBP"

    def test_detect_format_unknown(self, tmp_path):
        """Test unknown format detection."""
        unknown_data = b"UNKNOWN" + b'\x00' * 20

        img_path = tmp_path / "test.xyz"
        img_path.write_bytes(unknown_data)

        with pytest.raises(ContentValidationError, match="Unknown image format"):
            detect_image_format(img_path)


class TestImageDimensions:
    """Test image dimension reading."""

    def test_get_dimensions_png(self, tmp_path):
        """Test PNG dimension reading."""
        # Minimal PNG with dimensions
        png_data = (
            b"\x89PNG\r\n\x1a\n"  # Signature
            + b"\x00\x00\x00\rIHDR"  # IHDR chunk
            + b"\x00\x00\x00\x64"  # Width: 100
            + b"\x00\x00\x00\x96"  # Height: 150
            + b"\x08\x02\x00\x00\x00"  # Rest of IHDR
        )

        img_path = tmp_path / "test.png"
        img_path.write_bytes(png_data)

        width, height = get_image_dimensions(img_path)
        assert width == 100
        assert height == 150

    def test_get_dimensions_gif(self, tmp_path):
        """Test GIF dimension reading."""
        gif_data = (
            b"GIF89a"
            + b"\x64\x00"  # Width: 100 (little endian)
            + b"\x96\x00"  # Height: 150 (little endian)
            + b"\x00" * 20
        )

        img_path = tmp_path / "test.gif"
        img_path.write_bytes(gif_data)

        width, height = get_image_dimensions(img_path)
        assert width == 100
        assert height == 150


class TestHasExifData:
    """Test EXIF data detection."""

    def test_has_exif_false_for_png(self, tmp_path):
        """Test PNG has no EXIF."""
        png_data = b"\x89PNG\r\n\x1a\n" + b"\x00" * 20

        img_path = tmp_path / "test.png"
        img_path.write_bytes(png_data)

        assert not has_exif_data(img_path)

    def test_has_exif_false_for_non_exif_jpeg(self, tmp_path):
        """Test JPEG without EXIF."""
        jpeg_data = bytes([
            0xFF, 0xD8,  # SOI
            0xFF, 0xDB,  # DQT (not EXIF)
            0x00, 0x02,
        ]) + b'\x00' * 20

        img_path = tmp_path / "test.jpg"
        img_path.write_bytes(jpeg_data)

        assert not has_exif_data(img_path)
