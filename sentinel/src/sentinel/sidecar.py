"""Sidecar file generation for non-markdown files."""

from datetime import datetime, timezone
from logging import getLogger
from pathlib import Path
from typing import Optional

from sentinel.config import WatcherConfig


logger = getLogger(__name__)


def generate_sidecar(
    source: Path,
    dest: Path,
    config: WatcherConfig,
) -> Optional[Path]:
    """Generate sidecar .md file for non-markdown file.

    Args:
        source: Original file path (for metadata).
        dest: Destination file in inbox.
        config: Watcher configuration.

    Returns:
        Path to sidecar file, or None if no sidecar generated.
    """
    # Don't generate sidecar for .md files
    if dest.suffix.lower() == ".md":
        logger.debug(f"No sidecar for markdown: {dest.name}")
        return None

    # Generate sidecar metadata
    timestamp = datetime.now(timezone.utc).isoformat().replace(
        "+00:00",
        "Z",
    )
    file_size = dest.stat().st_size if dest.exists() else 0

    sidecar_name = f"{dest.name}.md"
    sidecar_path = dest.parent / sidecar_name

    # Render sidecar content
    content = _render_sidecar(
        original_filename=source.name,
        source_path=str(source),
        file_size_bytes=file_size,
        ingestion_timestamp=timestamp,
        file_extension=dest.suffix,
    )

    try:
        sidecar_path.write_text(content, encoding="utf-8")
        logger.info(f"Sidecar created: {sidecar_name}")
        return sidecar_path
    except Exception as e:
        logger.error(
            f"Sidecar creation failed: {e}",
            exc_info=True,
        )
        return None


def _render_sidecar(
    original_filename: str,
    source_path: str,
    file_size_bytes: int,
    ingestion_timestamp: str,
    file_extension: str,
) -> str:
    """Render sidecar markdown content.

    Args:
        original_filename: Original filename.
        source_path: Source file path.
        file_size_bytes: File size in bytes.
        ingestion_timestamp: ISO-8601 ingestion timestamp.
        file_extension: File extension (e.g., ".pdf").

    Returns:
        Sidecar markdown content.
    """
    size_kb = file_size_bytes / 1024

    return f"""---
type: sidecar
original_filename: "{original_filename}"
source_path: "{source_path}"
file_size_bytes: {file_size_bytes}
ingestion_timestamp: "{ingestion_timestamp}"
file_extension: "{file_extension}"
---

# {original_filename}

Ingested by Sentinel on {ingestion_timestamp}.

**Source**: `{source_path}`
**Size**: {file_size_bytes} bytes ({size_kb:.1f} KB)
**Type**: {file_extension}

> This file was automatically generated. The original file is stored alongside this sidecar.
"""
