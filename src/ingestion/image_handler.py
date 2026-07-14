"""Image upload and validation for phone photos and scanned images."""

from pathlib import Path

from PIL import Image

SUPPORTED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}
MIN_WIDTH = 640
MIN_HEIGHT = 480
MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB


class ImageValidationError(Exception):
    """Raised when an image fails validation checks."""


def validate_image(file_path: str | Path) -> None:
    """Validate that the file is a readable image meeting minimum requirements.

    Checks:
        - File exists and is non-empty.
        - Extension is in the supported set.
        - Pillow can open and read the file.
        - Dimensions are at least MIN_WIDTH x MIN_HEIGHT.
        - File size is under MAX_FILE_SIZE_BYTES.

    Raises:
        ImageValidationError: If any check fails.
    """
    path = Path(file_path)
    if not path.exists():
        raise ImageValidationError(f"File not found: {path}")
    if path.stat().st_size == 0:
        raise ImageValidationError(f"File is empty: {path}")
    if path.stat().st_size > MAX_FILE_SIZE_BYTES:
        raise ImageValidationError(
            f"File too large ({path.stat().st_size} bytes). "
            f"Maximum allowed is {MAX_FILE_SIZE_BYTES} bytes."
        )
    if path.suffix.lower() not in SUPPORTED_IMAGE_EXTENSIONS:
        raise ImageValidationError(
            f"Unsupported image format: {path.suffix}. "
            f"Supported: {', '.join(sorted(SUPPORTED_IMAGE_EXTENSIONS))}"
        )

    try:
        img = Image.open(str(path))
        img.verify()
    except Exception as exc:
        raise ImageValidationError(f"Cannot read image: {exc}") from exc

    # Re-open after verify() (verify closes the fp)
    img = Image.open(str(path))
    width, height = img.size
    if width < MIN_WIDTH or height < MIN_HEIGHT:
        raise ImageValidationError(
            f"Image too small ({width}x{height}). "
            f"Minimum resolution is {MIN_WIDTH}x{MIN_HEIGHT}."
        )


def get_image_info(file_path: str | Path) -> dict:
    """Return metadata about an image file."""
    path = Path(file_path)
    img = Image.open(str(path))
    width, height = img.size
    info = {
        "width": width,
        "height": height,
        "format": img.format,
        "mode": img.mode,
        "file_size_bytes": path.stat().st_size,
    }
    img.close()
    return info


def save_image(file_path: str | Path, output_path: str | Path) -> Path:
    """Copy / convert an image to the output path as PNG.

    Useful for normalizing uploaded phone photos into a consistent
    format for downstream OCR.
    """
    img = Image.open(str(file_path))
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    # Convert to RGB if necessary (e.g. RGBA or palette images)
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")
    img.save(str(output), format="PNG")
    img.close()
    return output
