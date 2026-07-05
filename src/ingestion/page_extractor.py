"""Extract individual pages from multi-page documents (PDFs)."""

from pathlib import Path

from src.ingestion.image_handler import ImageValidationError, validate_image
from src.ingestion.pdf_handler import (
    PDFValidationError,
    extract_all_pages,
    validate_pdf,
)


class PageExtractionError(Exception):
    """Raised when page extraction fails."""


def extract_pages_from_pdf(
    file_path: str | Path,
    output_dir: str | Path,
    dpi: int = 300,
) -> list[Path]:
    """Extract all pages from a PDF as PNG images.

    Validates the PDF first, then renders each page at the given DPI.

    Args:
        file_path: Path to the source PDF.
        output_dir: Directory to write page images into.
        dpi: Resolution for rendering (default 300).

    Returns:
        Ordered list of Paths to rendered page PNGs.

    Raises:
        PageExtractionError: If validation or extraction fails.
    """
    try:
        validate_pdf(file_path)
    except PDFValidationError as exc:
        raise PageExtractionError(str(exc)) from exc

    try:
        return extract_all_pages(file_path, output_dir, dpi=dpi)
    except Exception as exc:
        raise PageExtractionError(f"Page extraction failed: {exc}") from exc


def extract_pages_from_image(
    file_path: str | Path,
    output_dir: str | Path,
) -> list[Path]:
    """Store a single image as a 'page' for downstream processing.

    Validates the image and copies it to the output directory as PNG.

    Args:
        file_path: Path to the source image.
        output_dir: Directory to write the page image into.

    Returns:
        List with a single Path to the saved page image.

    Raises:
        PageExtractionError: If validation or saving fails.
    """
    try:
        validate_image(file_path)
    except ImageValidationError as exc:
        raise PageExtractionError(str(exc)) from exc

    try:
        src = Path(file_path)
        output = Path(output_dir)
        output.mkdir(parents=True, exist_ok=True)
        dest = output / "page_1.png"

        from src.ingestion.image_handler import save_image

        save_image(src, dest)
        return [dest]
    except Exception as exc:
        raise PageExtractionError(f"Image page extraction failed: {exc}") from exc
