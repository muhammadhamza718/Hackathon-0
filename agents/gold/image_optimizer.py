"""Image compression and optimization utilities.

Provides image optimization for social media posts with automatic
resizing, compression, and format conversion.
"""

from __future__ import annotations

import io
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ImageDimensions:
    """Image dimensions."""

    width: int
    height: int

    @property
    def aspect_ratio(self) -> float:
        """Get aspect ratio."""
        return self.width / self.height if self.height > 0 else 0

    @property
    def megapixels(self) -> float:
        """Get megapixels."""
        return (self.width * self.height) / 1_000_000


@dataclass
class PlatformImageSpec:
    """Image specifications for a platform."""

    platform: str
    max_width: int
    max_height: int
    max_file_size_kb: int
    recommended_format: str = "JPEG"
    quality: int = 85
    min_width: int = 0
    min_height: int = 0


# Platform-specific image specifications
PLATFORM_SPECS: dict[str, PlatformImageSpec] = {
    "X": PlatformImageSpec(
        platform="X",
        max_width=4096,
        max_height=4096,
        max_file_size_kb=5120,  # 5MB
        recommended_format="JPEG",
        quality=85,
        min_width=600,
        min_height=335,
    ),
    "Facebook": PlatformImageSpec(
        platform="Facebook",
        max_width=2048,
        max_height=2048,
        max_file_size_kb=8192,  # 8MB
        recommended_format="JPEG",
        quality=90,
    ),
    "Instagram": PlatformImageSpec(
        platform="Instagram",
        max_width=1080,
        max_height=1350,  # 4:5 portrait
        max_file_size_kb=8192,  # 8MB
        recommended_format="JPEG",
        quality=90,
        min_width=320,
        min_height=320,
    ),
}


class ImageOptimizer:
    """Optimizes images for social media platforms.

    Features:
    - Automatic resizing to platform specifications
    - Compression with quality control
    - Format conversion
    - Aspect ratio preservation
    """

    def __init__(self):
        """Initialize the image optimizer."""
        self.platform_specs = PLATFORM_SPECS

    def get_spec(self, platform: str) -> PlatformImageSpec:
        """Get image specifications for a platform.

        Args:
            platform: Platform name.

        Returns:
            Platform image specifications.

        Raises:
            ValueError: If platform not supported.
        """
        if platform not in self.platform_specs:
            raise ValueError(f"Unsupported platform: {platform}")
        return self.platform_specs[platform]

    def optimize(
        self,
        image_path: str | Path,
        platform: str = "X",
        output_path: str | Path | None = None,
    ) -> dict[str, Any]:
        """Optimize an image for a platform.

        Args:
            image_path: Path to the input image.
            platform: Target platform.
            output_path: Optional output path (default: auto-generated).

        Returns:
            Dictionary with optimization results.
        """
        image_path = Path(image_path)
        spec = self.get_spec(platform)

        if not image_path.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")

        # Read image
        try:
            from PIL import Image

            with Image.open(image_path) as img:
                original_dimensions = ImageDimensions(
                    width=img.width, height=img.height
                )

                # Convert to RGB if necessary
                if img.mode in ("RGBA", "P"):
                    img = img.convert("RGB")

                # Resize if needed
                img = self._resize(img, spec)

                # Optimize and save
                output_path = output_path or self._get_output_path(
                    image_path, platform
                )

                # Ensure output directory exists
                Path(output_path).parent.mkdir(parents=True, exist_ok=True)

                img.save(
                    output_path,
                    format=spec.recommended_format,
                    quality=spec.quality,
                    optimize=True,
                    progressive=True,
                )

                # Get output stats
                output_size_kb = Path(output_path).stat().st_size / 1024
                final_dimensions = ImageDimensions(
                    width=img.width, height=img.height
                )

                result = {
                    "success": True,
                    "input_path": str(image_path),
                    "output_path": str(output_path),
                    "platform": platform,
                    "original_dimensions": {
                        "width": original_dimensions.width,
                        "height": original_dimensions.height,
                    },
                    "final_dimensions": {
                        "width": final_dimensions.width,
                        "height": final_dimensions.height,
                    },
                    "original_size_kb": image_path.stat().st_size / 1024,
                    "final_size_kb": output_size_kb,
                    "compression_ratio": (
                        1 - output_size_kb / (image_path.stat().st_size / 1024)
                    )
                    * 100
                    if image_path.stat().st_size > 0
                    else 0,
                    "format": spec.recommended_format,
                    "quality": spec.quality,
                }

                logger.info(
                    f"Optimized {image_path.name} for {platform}: "
                    f"{result['compression_ratio']:.1f}% compression"
                )

                return result

        except ImportError:
            # PIL not available - return original path
            logger.warning(
                "PIL not available, returning original image"
            )
            return {
                "success": True,
                "input_path": str(image_path),
                "output_path": str(image_path),
                "platform": platform,
                "note": "PIL not available, image not optimized",
            }
        except Exception as e:
            logger.error(f"Failed to optimize image: {e}")
            return {
                "success": False,
                "input_path": str(image_path),
                "error": str(e),
            }

    def _resize(
        self, img: Any, spec: PlatformImageSpec
    ) -> Any:
        """Resize image to fit platform specifications.

        Args:
            img: PIL Image object.
            spec: Platform specifications.

        Returns:
            Resized PIL Image.
        """
        from PIL import Image

        original_width, original_height = img.size

        # Check if resize needed
        if (
            original_width <= spec.max_width
            and original_height <= spec.max_height
        ):
            return img

        # Calculate new dimensions preserving aspect ratio
        ratio = min(
            spec.max_width / original_width,
            spec.max_height / original_height,
        )

        new_width = int(original_width * ratio)
        new_height = int(original_height * ratio)

        # Use high-quality resampling
        return img.resize(
            (new_width, new_height), Image.Resampling.LANCZOS
        )

    def _get_output_path(
        self, input_path: Path, platform: str
    ) -> Path:
        """Generate output path for optimized image.

        Args:
            input_path: Original image path.
            platform: Target platform.

        Returns:
            Output path.
        """
        spec = self.get_spec(platform)
        suffix = f"_optimized_{platform.lower()}.{spec.recommended_format.lower()}"
        return input_path.with_name(input_path.stem + suffix)

    def optimize_multiple(
        self,
        image_paths: list[str | Path],
        platform: str = "X",
        output_dir: str | Path | None = None,
    ) -> list[dict[str, Any]]:
        """Optimize multiple images for a platform.

        Args:
            image_paths: List of image paths.
            platform: Target platform.
            output_dir: Optional output directory.

        Returns:
            List of optimization results.
        """
        results = []

        if output_dir:
            Path(output_dir).mkdir(parents=True, exist_ok=True)

        for path in image_paths:
            output_path = (
                Path(output_dir) / Path(path).name
                if output_dir
                else None
            )
            result = self.optimize(path, platform, output_path)
            results.append(result)

        return results

    def validate_image(
        self, image_path: str | Path, platform: str = "X"
    ) -> dict[str, Any]:
        """Validate an image against platform specifications.

        Args:
            image_path: Path to the image.
            platform: Target platform.

        Returns:
            Validation results.
        """
        image_path = Path(image_path)
        spec = self.get_spec(platform)

        if not image_path.exists():
            return {
                "valid": False,
                "error": f"Image not found: {image_path}",
            }

        try:
            from PIL import Image

            with Image.open(image_path) as img:
                dimensions = ImageDimensions(width=img.width, height=img.height)
                file_size_kb = image_path.stat().st_size / 1024

                issues = []

                if dimensions.width > spec.max_width:
                    issues.append(
                        f"Width {dimensions.width} exceeds max {spec.max_width}"
                    )
                if dimensions.height > spec.max_height:
                    issues.append(
                        f"Height {dimensions.height} exceeds max {spec.max_height}"
                    )
                if dimensions.width < spec.min_width:
                    issues.append(
                        f"Width {dimensions.width} below min {spec.min_width}"
                    )
                if dimensions.height < spec.min_height:
                    issues.append(
                        f"Height {dimensions.height} below min {spec.min_height}"
                    )
                if file_size_kb > spec.max_file_size_kb:
                    issues.append(
                        f"Size {file_size_kb:.1f}KB exceeds max {spec.max_file_size_kb}KB"
                    )

                return {
                    "valid": len(issues) == 0,
                    "dimensions": {
                        "width": dimensions.width,
                        "height": dimensions.height,
                    },
                    "file_size_kb": file_size_kb,
                    "format": img.format,
                    "issues": issues,
                }

        except ImportError:
            return {
                "valid": True,
                "note": "PIL not available, basic validation only",
                "file_size_kb": image_path.stat().st_size / 1024,
            }
        except Exception as e:
            return {
                "valid": False,
                "error": str(e),
            }
