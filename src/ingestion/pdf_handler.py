"""PDF processing and page extraction via PyMuPDF (fitz)."""

from pathlib import Path

import fitz  # PyMuPDF


class PDFValidationError(Exception):
    """Raised when a PDF file fails validation."""


def validate_pdf(file_path: str | Path) -> None:
    """Validate that the file is a readable, non-corrupted PDF.

    Raises:
        PDFValidationError: If the file cannot be opened or is not a valid PDF.
    """
    path = Path(file_path)
    if not path.exists():
        raise PDFValidationError(f"File not found: {path}")
    if path.stat().st_size == 0:
        raise PDFValidationError(f"File is empty: {path}")
    try:
        doc = fitz.open(str(path))
        doc.close()
    except Exception as exc:
        raise PDFValidationError(f"Invalid PDF file: {exc}") from exc


def get_pdf_metadata(file_path: str | Path) -> dict:
    """Return basic metadata from a PDF (page count, title, author)."""
    doc = fitz.open(str(file_path))
    metadata = {
        "page_count": doc.page_count,
        "title": metadata_safe(doc, "title"),
        "author": metadata_safe(doc, "author"),
        "file_size_bytes": Path(file_path).stat().st_size,
    }
    doc.close()
    return metadata


def extract_pdf_page_as_image(
    file_path: str | Path,
    page_number: int,
    output_path: str | Path,
    dpi: int = 300,
) -> Path:
    """Render a single PDF page to a PNG image at the specified DPI.

    Args:
        file_path: Path to the PDF.
        page_number: Zero-indexed page number.
        output_path: Destination path for the rendered PNG.
        dpi: Resolution for rendering (default 300).

    Returns:
        Path to the saved PNG image.
    """
    doc = fitz.open(str(file_path))
    total = doc.page_count
    if page_number < 0 or page_number >= total:
        doc.close()
        raise PDFValidationError(f"Page {page_number} out of range (0-{total - 1})")

    page = doc[page_number]
    zoom = dpi / 72.0
    matrix = fitz.Matrix(zoom, zoom)
    pixmap = page.get_pixmap(matrix=matrix)
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    pixmap.save(str(output))
    doc.close()
    return output


def extract_all_pages(
    file_path: str | Path,
    output_dir: str | Path,
    dpi: int = 300,
) -> list[Path]:
    """Extract every page of a PDF as individual PNG images.

    Args:
        file_path: Path to the PDF.
        output_dir: Directory to save page images into.
        dpi: Resolution for rendering.

    Returns:
        List of Paths to the rendered PNG files, in page order.
    """
    doc = fitz.open(str(file_path))
    pages: list[Path] = []
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    zoom = dpi / 72.0
    matrix = fitz.Matrix(zoom, zoom)

    for idx in range(doc.page_count):
        page = doc[idx]
        pixmap = page.get_pixmap(matrix=matrix)
        page_path = output / f"page_{idx + 1}.png"
        pixmap.save(str(page_path))
        pages.append(page_path)

    doc.close()
    return pages


def metadata_safe(doc: fitz.Document, key: str) -> str | None:
    """Safely extract a metadata field from a fitz Document."""
    try:
        value = doc.metadata.get(key)
        return value if value else None
    except Exception:
        return None
