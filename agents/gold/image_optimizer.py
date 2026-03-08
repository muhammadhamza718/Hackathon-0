"""Image optimization and validation for social media posts.

Provides image validation, compression, format conversion, and EXIF data
stripping for privacy compliance. All operations respect platform-specific
image limits.
"""

from __future__ import annotations

import io
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from agents.exceptions import ContentValidationError, SocialMediaError

# ---------------------------------------------------------------------------
# Platform-specific image limits
# ---------------------------------------------------------------------------

IMAGE_FORMAT = Literal["JPEG", "PNG", "GIF", "WEBP"]

PLATFORM_IMAGE_LIMITS: dict[str, dict] = {
    "X": {
        "max_file_size_mb": 5,
        "max_width": 4096,
        "max_height": 4096,
        "supported_formats": ["JPEG", "PNG", "GIF", "WEBP"],
        "recommended_format": "JPEG",
        "quality": 85,
    },
    "Facebook": {
        "max_file_size_mb": 15,
        "max_width": 2048,
        "max_height": 2048,
        "supported_formats": ["JPEG", "PNG", "GIF", "WEBP"],
        "recommended_format": "JPEG",
        "quality": 90,
    },
    "Instagram": {
        "max_file_size_mb": 8,
        "max_width": 1080,
        "max_height": 1350,
        "supported_formats": ["JPEG", "PNG"],
        "recommended_format": "JPEG",
        "quality": 90,
        "aspect_ratio_min": 0.5,  # 4:5 portrait
        "aspect_ratio_max": 1.91,  # 1.91:1 landscape
    },
}


@dataclass
class ImageInfo:
    """Information about an image file."""

    path: str
    format: str
    width: int
    height: int
    file_size_bytes: int
    has_exif: bool
    aspect_ratio: float


@dataclass
class OptimizationResult:
    """Result of image optimization."""

    original_path: str
    optimized_path: str
    original_size_bytes: int
    optimized_size_bytes: int
    compression_ratio: float
    format_changed: bool
    exif_stripped: bool
    dimensions_changed: bool
    warnings: list[str]


def get_image_dimensions(path: Path) -> tuple[int, int]:
    """Get image dimensions without loading full image.

    Supports JPEG, PNG, GIF, and WEBP formats.

    Args:
        path: Path to the image file.

    Returns:
        Tuple of (width, height).

    Raises:
        ContentValidationError: If format is unsupported or file is corrupt.
    """
    with open(path, "rb") as f:
        header = f.read(32)

        # JPEG
        if header[:2] == b"\xFF\xD8":
            f.seek(0)
            size = 2
            ftype = 0
            while not 0xC0 <= ftype <= 0xCF or ftype in (0xC4, 0xC8, 0xCC):
                f.seek(size, 1)
                byte = f.read(1)
                while byte == b"\xFF":
                    byte = f.read(1)
                ftype = ord(byte)
                size = struct.unpack(">H", f.read(2))[0] - 2
            f.seek(1, 1)
            height, width = struct.unpack(">HH", f.read(4))
            return width, height

        # PNG
        if header[:8] == b"\x89PNG\r\n\x1a\n":
            width, height = struct.unpack(">II", header[16:24])
            return width, height

        # GIF
        if header[:6] in (b"GIF87a", b"GIF89a"):
            width, height = struct.unpack("<HH", header[6:10])
            return width, height

        # WEBP
        if header[:4] == b"RIFF" and header[8:12] == b"WEBP":
            # VP8 header
            f.seek(26)
            chunk_header = f.read(8)
            if chunk_header[:4] == b"VP8 ":
                # Lossy
                f.seek(6, 1)
                width, height = struct.unpack("<HH", f.read(4))
                return width, height
            elif chunk_header[:4] == b"VP8L":
                # Lossless
                bits = f.read(5)
                width = (bits[1] | ((bits[2] & 0x3F) << 8)) + 1
                height = (
                    ((bits[2] & 0xC0) >> 6)
                    | (bits[3] << 2)
                    | ((bits[4] & 0x03) << 10)
                ) + 1
                return width, height

        raise ContentValidationError(f"Unsupported or corrupt image format: {path}")


def detect_image_format(path: Path) -> str:
    """Detect image format from file header.

    Args:
        path: Path to the image file.

    Returns:
        Format string (JPEG, PNG, GIF, WEBP).

    Raises:
        ContentValidationError: If format cannot be detected.
    """
    with open(path, "rb") as f:
        header = f.read(12)

        if header[:2] == b"\xFF\xD8":
            return "JPEG"
        if header[:8] == b"\x89PNG\r\n\x1a\n":
            return "PNG"
        if header[:6] in (b"GIF87a", b"GIF89a"):
            return "GIF"
        if header[:4] == b"RIFF" and header[8:12] == b"WEBP":
            return "WEBP"

        # Try extension-based detection as fallback
        ext = path.suffix.lower()
        ext_map = {
            ".jpg": "JPEG",
            ".jpeg": "JPEG",
            ".png": "PNG",
            ".gif": "GIF",
            ".webp": "WEBP",
        }
        if ext in ext_map:
            return ext_map[ext]

        raise ContentValidationError(f"Unknown image format: {path}")


def has_exif_data(path: Path) -> bool:
    """Check if JPEG image contains EXIF data.

    Args:
        path: Path to the image file.

    Returns:
        True if EXIF data is present.
    """
    if detect_image_format(path) != "JPEG":
        return False

    with open(path, "rb") as f:
        # Check for APP1 marker (EXIF)
        if f.read(2) != b"\xFF\xD8":
            return False

        while True:
            marker = f.read(2)
            if len(marker) < 2:
                return False

            if marker[0] != 0xFF:
                return False

            # APP1 marker
            if marker[1] == 0xE1:
                size = struct.unpack(">H", f.read(2))[0]
                exif_header = f.read(6)
                return exif_header == b"Exif\x00\x00"

            # SOS marker (start of scan - no more headers after this)
            if marker[1] == 0xDA:
                return False

            # Skip this segment
            if marker[1] != 0xD8:  # Not SOI
                size = struct.unpack(">H", f.read(2))[0]
                f.seek(size - 2, 1)


def validate_image(
    path: str | Path,
    platform: str,
) -> ImageInfo:
    """Validate image against platform requirements.

    Args:
        path: Path to the image file.
        platform: Target platform (X, Facebook, Instagram).

    Returns:
        ImageInfo with validation details.

    Raises:
        ContentValidationError: If image fails validation.
        SocialMediaError: If platform is unknown.
    """
    path = Path(path)
    limits = PLATFORM_IMAGE_LIMITS.get(platform)

    if limits is None:
        raise SocialMediaError(f"Unknown platform: {platform}")

    if not path.exists():
        raise ContentValidationError(f"Image file not found: {path}")

    # Detect format
    img_format = detect_image_format(path)
    if img_format not in limits["supported_formats"]:
        raise ContentValidationError(
            f"Unsupported format '{img_format}' for {platform}. "
            f"Supported: {limits['supported_formats']}"
        )

    # Get dimensions
    width, height = get_image_dimensions(path)

    # Check dimensions
    if width > limits["max_width"]:
        raise ContentValidationError(
            f"Image width {width}px exceeds {platform} limit of {limits['max_width']}px"
        )
    if height > limits["max_height"]:
        raise ContentValidationError(
            f"Image height {height}px exceeds {platform} limit of {limits['max_height']}px"
        )

    # Check file size
    file_size = path.stat().st_size
    max_size_bytes = limits["max_file_size_mb"] * 1024 * 1024
    if file_size > max_size_bytes:
        raise ContentValidationError(
            f"Image size {file_size / 1024 / 1024:.1f}MB exceeds "
            f"{platform} limit of {limits['max_file_size_mb']}MB"
        )

    # Check aspect ratio for Instagram
    if platform == "Instagram":
        aspect_ratio = width / height if height > 0 else 0
        if aspect_ratio < limits["aspect_ratio_min"]:
            raise ContentValidationError(
                f"Aspect ratio {aspect_ratio:.2f} too narrow for Instagram "
                f"(min: {limits['aspect_ratio_min']})"
            )
        if aspect_ratio > limits["aspect_ratio_max"]:
            raise ContentValidationError(
                f"Aspect ratio {aspect_ratio:.2f} too wide for Instagram "
                f"(max: {limits['aspect_ratio_max']})"
            )
    else:
        aspect_ratio = width / height if height > 0 else 0

    return ImageInfo(
        path=str(path),
        format=img_format,
        width=width,
        height=height,
        file_size_bytes=file_size,
        has_exif=has_exif_data(path),
        aspect_ratio=aspect_ratio,
    )


def optimize_image(
    path: str | Path,
    platform: str,
    output_dir: Path | None = None,
    strip_exif: bool = True,
    target_format: IMAGE_FORMAT | None = None,
) -> OptimizationResult:
    """Optimize image for social media platform.

    Performs:
    - Format conversion if needed
    - Compression with quality adjustment
    - EXIF data stripping for privacy
    - Dimension resizing if needed

    Args:
        path: Path to source image.
        platform: Target platform for optimization.
        output_dir: Directory for optimized image (default: same as source).
        strip_exif: Whether to remove EXIF data (default: True for privacy).
        target_format: Target format (default: platform recommended).

    Returns:
        OptimizationResult with details of changes made.

    Raises:
        ContentValidationError: If validation fails.
        SocialMediaError: If optimization fails.

    Note:
        Requires Pillow library for image processing.
        If Pillow is not available, returns path unchanged with warnings.
    """
    path = Path(path)
    limits = PLATFORM_IMAGE_LIMITS.get(platform)

    if limits is None:
        raise SocialMediaError(f"Unknown platform: {platform}")

    if output_dir is None:
        output_dir = path.parent

    # Validate first
    info = validate_image(path, platform)

    warnings: list[str] = []
    format_changed = False
    exif_stripped = False
    dimensions_changed = False

    # Try to use Pillow for optimization
    try:
        from PIL import Image

        # Open image
        img = Image.open(path)

        # Determine target format
        if target_format is None:
            target_format = limits["recommended_format"]

        if target_format != info.format:
            format_changed = True
            warnings.append(f"Converting from {info.format} to {target_format}")

        # Convert mode if needed
        if target_format == "JPEG" and img.mode in ("RGBA", "LA", "P"):
            # Create white background for transparency
            background = Image.new("RGB", img.size, (255, 255, 255))
            if img.mode == "P":
                img = img.convert("RGBA")
            background.paste(img, mask=img.split()[-1] if img.mode == "RGBA" else None)
            img = background
        elif img.mode != "RGB" and target_format == "JPEG":
            img = img.convert("RGB")

        # Resize if needed
        original_width, original_height = img.size
        if original_width > limits["max_width"] or original_height > limits["max_height"]:
            # Calculate new dimensions maintaining aspect ratio
            ratio = min(
                limits["max_width"] / original_width,
                limits["max_height"] / original_height,
            )
            new_width = int(original_width * ratio)
            new_height = int(original_height * ratio)
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            dimensions_changed = True
            warnings.append(f"Resized from {original_width}x{original_height} to {new_width}x{new_height}")

        # Save with optimization
        output_filename = f"optimized_{path.stem}.{target_format.lower()}"
        if target_format == "JPEG":
            output_filename = f"optimized_{path.stem}.jpg"
        output_path = output_dir / output_filename

        # Ensure output dir exists
        output_dir.mkdir(parents=True, exist_ok=True)

        # Save with quality setting
        save_kwargs: dict = {"quality": limits["quality"], "optimize": True}

        if strip_exif and target_format == "JPEG":
            save_kwargs["exif"] = b""
            exif_stripped = True
        elif strip_exif:
            # For PNG, don't save metadata
            pass

        if target_format == "WEBP":
            save_kwargs["method"] = 6  # Best compression

        img.save(output_path, format=target_format, **save_kwargs)

        # Calculate results
        optimized_size = output_path.stat().st_size
        compression_ratio = (1 - optimized_size / info.file_size_bytes) * 100

        return OptimizationResult(
            original_path=str(path),
            optimized_path=str(output_path),
            original_size_bytes=info.file_size_bytes,
            optimized_size_bytes=optimized_size,
            compression_ratio=compression_ratio,
            format_changed=format_changed,
            exif_stripped=exif_stripped,
            dimensions_changed=dimensions_changed,
            warnings=warnings,
        )

    except ImportError:
        warnings.append("Pillow not available - skipping optimization")
        warnings.append("Install with: pip install Pillow")
        return OptimizationResult(
            original_path=str(path),
            optimized_path=str(path),
            original_size_bytes=info.file_size_bytes,
            optimized_size_bytes=info.file_size_bytes,
            compression_ratio=0.0,
            format_changed=False,
            exif_stripped=False,
            dimensions_changed=False,
            warnings=warnings,
        )
    except Exception as e:
        raise SocialMediaError(f"Image optimization failed: {e}") from e


def validate_and_optimize_images(
    media_paths: list[str | Path],
    platform: str,
    output_dir: Path | None = None,
) -> list[OptimizationResult]:
    """Validate and optimize multiple images for a platform.

    Args:
        media_paths: List of image paths to process.
        platform: Target platform.
        output_dir: Directory for optimized images.

    Returns:
        List of OptimizationResult for each image.

    Raises:
        ContentValidationError: If any image fails validation.
    """
    results: list[OptimizationResult] = []

    for path in media_paths:
        # Validate
        validate_image(path, platform)

        # Optimize
        result = optimize_image(path, platform, output_dir)
        results.append(result)

    return results


def get_optimization_summary(results: list[OptimizationResult]) -> dict:
    """Generate summary of image optimization results.

    Args:
        results: List of optimization results.

    Returns:
        Summary dict with totals and averages.
    """
    if not results:
        return {
            "total_images": 0,
            "total_original_size_mb": 0,
            "total_optimized_size_mb": 0,
            "total_savings_mb": 0,
            "average_compression_pct": 0,
            "format_changes": 0,
            "exif_stripped_count": 0,
        }

    total_original = sum(r.original_size_bytes for r in results)
    total_optimized = sum(r.optimized_size_bytes for r in results)

    return {
        "total_images": len(results),
        "total_original_size_mb": total_original / 1024 / 1024,
        "total_optimized_size_mb": total_optimized / 1024 / 1024,
        "total_savings_mb": (total_original - total_optimized) / 1024 / 1024,
        "average_compression_pct": sum(r.compression_ratio for r in results) / len(results),
        "format_changes": sum(1 for r in results if r.format_changed),
        "exif_stripped_count": sum(1 for r in results if r.exif_stripped),
    }
