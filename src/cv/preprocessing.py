"""Image preprocessing for OCR (deskew, denoise, binarize)."""

import argparse
import os

import cv2
import numpy as np


def deskew(image: np.ndarray) -> np.ndarray:
    """Deskew (straighten) an image by detecting structural lines.

    Uses Hough Transform to detect horizontal lines (table borders, underlines).
    Falls back to minAreaRect of all text pixels if no structural lines are found.
    """
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image

    edges = cv2.Canny(gray, 50, 150, apertureSize=3)
    lines = cv2.HoughLinesP(
        edges, 1, np.pi / 180, threshold=100, minLineLength=100, maxLineGap=10
    )

    angle = 0.0

    if lines is not None:
        # Only use near-horizontal lines to avoid 90-degree flips from margins
        angles = []
        for x1, y1, x2, y2 in lines.reshape(-1, 4):
            angle_deg = np.degrees(np.arctan2(y2 - y1, x2 - x1))
            if -45 <= angle_deg <= 45:
                angles.append(angle_deg)
        if angles:
            angle = np.median(angles)
    else:
        # Fallback: compute angle from bounding box of all text pixels
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)
        contours = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[
            -2
        ]
        if contours:
            rect_angle = cv2.minAreaRect(contours[0])[-1]
            angle = -(90 + rect_angle) if rect_angle < -45 else -rect_angle

    if abs(angle) < 0.1:
        return image

    h, w = image.shape[:2]
    M = cv2.getRotationMatrix2D((w // 2, h // 2), angle, 1.0)
    return cv2.warpAffine(image, M, (w, h), borderMode=cv2.BORDER_REPLICATE)


def denoise(image: np.ndarray, h: int = 10) -> np.ndarray:
    """Remove noise from an image while preserving text edges.

    Args:
        image: Input image (BGR or grayscale).
        h: Filter strength. Higher values remove more noise but may blur text.
    """
    if len(image.shape) == 3:
        return cv2.fastNlMeansDenoisingColored(image, None, h, h)
    return cv2.fastNlMeansDenoising(image, None, h)


def binarize(image: np.ndarray, block_size: int = 11, C: int = 2) -> np.ndarray:
    """Convert image to pure black-and-white using adaptive thresholding.

    Adaptive thresholding calculates the threshold per small region, making
    it robust to uneven lighting across the page.

    Args:
        image: Input image (BGR or grayscale).
        block_size: Size of the pixel neighbourhood used to calculate threshold.
        C: Constant subtracted from the mean. Higher values produce lighter output.
    """
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
    return cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, block_size, C
    )


def apply_clahe(
    image: np.ndarray, clip_limit: float = 2.0, tile_size: tuple = (8, 8)
) -> np.ndarray:
    """Enhance contrast using CLAHE (Contrast Limited Adaptive Histogram Equalization).

    Operates on small image tiles independently, making it effective at fixing
    uneven shadows across the page.

    Args:
        image: Input image (BGR or grayscale).
        clip_limit: Threshold for contrast limiting. Higher = more contrast boost.
        tile_size: Size of the grid tiles for local histogram equalization.
    """
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=tile_size)
    return clahe.apply(gray)


def preprocess_image(
    image: np.ndarray,
    do_deskew: bool = True,
    do_denoise: bool = True,
    do_binarize: bool = True,
    do_clahe: bool = True,
) -> np.ndarray:
    """Run the full preprocessing pipeline on a raw exam image.

    Args:
        image: Input BGR image (e.g. loaded with cv2.imread).
        do_deskew: Whether to run rotation correction.
        do_denoise: Whether to run noise removal.
        do_binarize: Whether to convert to black-and-white.
        do_clahe: Whether to run contrast enhancement.

    Returns:
        Cleaned, straightened image ready for OCR.
    """
    result = image.copy()
    if do_deskew:
        result = deskew(result)
    if do_denoise:
        result = denoise(result)
    if do_clahe:
        result = apply_clahe(result)
    if do_binarize:
        result = binarize(result)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test image preprocessing pipeline")
    parser.add_argument("--input", type=str, required=True, help="Input image path")
    parser.add_argument(
        "--output", type=str, default="preprocessed.png", help="Output path"
    )
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"Error: Input file '{args.input}' not found.")
        raise SystemExit(1)

    img = cv2.imread(args.input)
    if img is None:
        print(f"Error: Failed to load image '{args.input}'")
        raise SystemExit(1)

    print(f"Processing: {args.input}  shape={img.shape}")
    result = preprocess_image(img)
    cv2.imwrite(args.output, result)
    print(f"Saved to: {args.output}")
