"""Tests for sidecar generation."""

import pytest
from pathlib import Path
from sentinel.sidecar import generate_sidecar, _render_sidecar
from sentinel.config import WatcherConfig


def test_render_sidecar_markdown():
    """Test sidecar markdown generation."""
    content = _render_sidecar(
        original_filename="invoice.pdf",
        source_path="/home/user/Documents/invoice.pdf",
        file_size_bytes=245760,
        ingestion_timestamp="2026-02-20T12:00:00Z",
        file_extension=".pdf",
    )

    assert "---" in content  # YAML frontmatter
    assert "original_filename: \"invoice.pdf\"" in content
    assert "source_path: \"/home/user/Documents/invoice.pdf\"" in content
    assert "file_size_bytes: 245760" in content
    assert "ingestion_timestamp: \"2026-02-20T12:00:00Z\"" in content
    assert "file_extension: \".pdf\"" in content
    assert "# invoice.pdf" in content


def test_generate_sidecar_pdf(mock_config):
    """Test sidecar generation for PDF."""
    # Create PDF file in inbox
    pdf_file = mock_config.vault_inbox_path / "invoice.pdf"
    pdf_file.write_bytes(b"PDF content")

    source = mock_config.watch_directory / "invoice.pdf"

    sidecar = generate_sidecar(source, pdf_file, mock_config)

    assert sidecar is not None
    assert sidecar.exists()
    assert sidecar.name == "invoice.pdf.md"
    assert sidecar.parent == mock_config.vault_inbox_path

    content = sidecar.read_text()
    assert "original_filename: \"invoice.pdf\"" in content
    assert "file_extension: \".pdf\"" in content


def test_generate_sidecar_jpg(mock_config):
    """Test sidecar generation for JPG."""
    jpg_file = mock_config.vault_inbox_path / "photo.jpg"
    jpg_file.write_bytes(b"JPG content")

    source = mock_config.watch_directory / "photo.jpg"

    sidecar = generate_sidecar(source, jpg_file, mock_config)

    assert sidecar is not None
    assert sidecar.exists()
    assert sidecar.name == "photo.jpg.md"

    content = sidecar.read_text()
    assert "original_filename: \"photo.jpg\"" in content
    assert "file_extension: \".jpg\"" in content


def test_no_sidecar_for_markdown(mock_config):
    """Test no sidecar generated for .md files."""
    md_file = mock_config.vault_inbox_path / "note.md"
    md_file.write_text("# Note")

    source = mock_config.watch_directory / "note.md"

    sidecar = generate_sidecar(source, md_file, mock_config)

    assert sidecar is None
    # No .md.md file should exist
    assert not (mock_config.vault_inbox_path / "note.md.md").exists()


def test_sidecar_size_formatting(mock_config):
    """Test sidecar shows file size in bytes and KB."""
    # Create a larger file
    large_file = mock_config.vault_inbox_path / "data.pdf"
    large_file.write_bytes(b"X" * 102400)  # 100 KB

    source = mock_config.watch_directory / "data.pdf"

    sidecar = generate_sidecar(source, large_file, mock_config)

    content = sidecar.read_text()
    assert "102400" in content  # Bytes
    assert "100.0" in content or "100.0 KB" in content
