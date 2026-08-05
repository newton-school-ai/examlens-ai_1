"""Line-aware handwritten OCR using Microsoft's TrOCR model.

The transformer dependencies and model weights are loaded lazily.  Importing
this module therefore remains cheap for API workers which do not process
handwriting.
"""

from __future__ import annotations

import argparse
import os
from typing import Any, Literal

import cv2
import numpy as np
from PIL import Image
from pydantic import BaseModel, Field

try:
    import pytesseract
    from pytesseract import Output, TesseractError, TesseractNotFoundError
except ImportError:  # pragma: no cover - exercised only in minimal installations
    pytesseract = None
    Output = None
    TesseractError = TesseractNotFoundError = RuntimeError

from src.config.settings import settings
from src.cv.preprocessing import deskew

LineType = Literal["handwritten", "printed"]
PageType = Literal["handwritten", "printed", "mixed", "empty"]

_trocr_processor: Any | None = None
_trocr_model: Any | None = None
_trocr_model_name: str | None = None


class LineRegion(BaseModel):
    """Coordinates of one detected text line."""

    x: int
    y: int
    width: int
    height: int


class HandwrittenLine(LineRegion):
    """Recognized line plus the information needed by a correction UI."""

    text: str
    confidence: float = Field(ge=0.0, le=1.0)
    line_type: LineType = "handwritten"
    needs_correction: bool = False


class HandwrittenOCRResult(BaseModel):
    """Structured result for a handwritten or mixed page."""

    text: str
    lines: list[HandwrittenLine]
    confidence: float = Field(ge=0.0, le=1.0)
    page_type: PageType
    engine: str


def get_trocr_model(model_name: str | None = None) -> tuple[Any, Any]:
    """Return a cached TrOCR processor/model pair configured for CPU."""
    global _trocr_model, _trocr_model_name, _trocr_processor
    selected_model = model_name or settings.trocr_model
    if (
        _trocr_processor is None
        or _trocr_model is None
        or _trocr_model_name != selected_model
    ):
        try:
            from transformers import TrOCRProcessor, VisionEncoderDecoderModel
        except ImportError as exc:  # pragma: no cover - depends on local extras
            raise RuntimeError(
                "TrOCR requires transformers and torch. Install project "
                "dependencies with `pip install -r requirements.txt`."
            ) from exc

        _trocr_processor = TrOCRProcessor.from_pretrained(selected_model)
        _trocr_model = VisionEncoderDecoderModel.from_pretrained(selected_model)
        _trocr_model.to("cpu")
        _trocr_model.eval()
        _trocr_model_name = selected_model
    return _trocr_processor, _trocr_model


def _foreground_mask(image: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 else image
    if max(gray.shape) > 2200:
        scale = 2200 / max(gray.shape)
        gray = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    blurred = cv2.GaussianBlur(gray, (3, 3), 0)
    return cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)[1]


def _remove_page_rules(mask: np.ndarray, aggressive: bool = False) -> np.ndarray:
    """Remove long notebook/table rules without erasing normal character strokes."""
    horizontal_kernel = cv2.getStructuringElement(
        cv2.MORPH_RECT, (max(30, mask.shape[1] // 12), 1)
    )
    vertical_kernel = cv2.getStructuringElement(
        cv2.MORPH_RECT,
        (
            1,
            max(30, mask.shape[0] // 12) if aggressive else max(80, mask.shape[0] // 6),
        ),
    )
    horizontal = cv2.morphologyEx(mask, cv2.MORPH_OPEN, horizontal_kernel)
    vertical = cv2.morphologyEx(mask, cv2.MORPH_OPEN, vertical_kernel)
    return cv2.subtract(mask, cv2.bitwise_or(horizontal, vertical))


def _projection_line_regions(
    mask: np.ndarray, original_width: int, original_height: int
) -> list[LineRegion]:
    """Split connected cursive/grid pages at stable horizontal ink peaks."""
    row_density = np.count_nonzero(mask, axis=1).astype(np.float32) / max(
        1, mask.shape[1]
    )
    kernel_height = max(7, round(mask.shape[0] / 65))
    if kernel_height % 2 == 0:
        kernel_height += 1
    smoothed = cv2.GaussianBlur(
        row_density.reshape(-1, 1), (1, kernel_height), 0
    ).ravel()
    if not np.any(smoothed):
        return []

    peak_threshold = max(0.01, float(smoothed.max()) * 0.25)
    candidates = [
        index
        for index in range(1, len(smoothed) - 1)
        if smoothed[index] >= smoothed[index - 1]
        and smoothed[index] > smoothed[index + 1]
        and smoothed[index] >= peak_threshold
    ]
    minimum_distance = max(12, mask.shape[0] // 25)
    selected: list[int] = []
    for index in sorted(candidates, key=lambda item: smoothed[item], reverse=True):
        if all(abs(index - existing) >= minimum_distance for existing in selected):
            selected.append(index)
    selected.sort()
    if not selected:
        return []

    if len(selected) == 1:
        half_gap = max(8, mask.shape[0] // 20)
        boundaries = [selected[0] - half_gap, selected[0] + half_gap]
    else:
        typical_gap = int(np.median(np.diff(selected)))
        boundaries = [selected[0] - typical_gap // 2]
        boundaries.extend(
            (first + second) // 2 for first, second in zip(selected, selected[1:])
        )
        boundaries.append(selected[-1] + typical_gap // 2)

    scale_x = original_width / mask.shape[1]
    scale_y = original_height / mask.shape[0]
    regions: list[LineRegion] = []
    for index in range(len(selected)):
        top = max(0, boundaries[index])
        bottom = min(mask.shape[0], boundaries[index + 1])
        band = mask[top:bottom]
        points_y, points_x = np.where(band > 0)
        if points_x.size == 0:
            continue
        left = int(np.percentile(points_x, 1))
        right = int(np.percentile(points_x, 99)) + 1
        if right - left < max(12, mask.shape[1] // 100):
            continue
        regions.append(
            LineRegion(
                x=round(left * scale_x),
                y=round(top * scale_y),
                width=max(1, round((right - left) * scale_x)),
                height=max(1, round((bottom - top) * scale_y)),
            )
        )
    return regions


def _merge_line_boxes(
    boxes: list[tuple[int, int, int, int]], image_width: int
) -> list[LineRegion]:
    """Join word contours that occupy the same baseline."""
    groups: list[list[int]] = []
    for x, y, width, height in sorted(boxes, key=lambda box: (box[1], box[0])):
        centre = y + height / 2
        match: list[int] | None = None
        best_distance = float("inf")
        for group in groups:
            group_centre = (group[1] + group[3]) / 2
            tolerance = max(height, group[3] - group[1]) * 0.65
            if abs(centre - group_centre) <= tolerance:
                distance = abs(centre - group_centre)
                if distance < best_distance:
                    match, best_distance = group, distance
        if match is None:
            groups.append([x, y, x + width, y + height])
        else:
            match[0] = min(match[0], x)
            match[1] = min(match[1], y)
            match[2] = max(match[2], x + width)
            match[3] = max(match[3], y + height)

    regions: list[LineRegion] = []
    for left, top, right, bottom in groups:
        width, height = right - left, bottom - top
        if width >= max(12, image_width // 100) and height >= 4:
            regions.append(LineRegion(x=left, y=top, width=width, height=height))
    return sorted(regions, key=lambda region: (region.y, region.x))


def segment_text_lines(image: np.ndarray) -> list[LineRegion]:
    """Detect text lines using morphology and baseline-aware box grouping.

    This is deliberately model-free: it works offline, is fast on CPU, and
    handles disconnected cursive words better than row projection alone.
    """
    if image is None or image.size == 0:
        raise ValueError("A non-empty image is required for line segmentation")

    original_height, original_width = image.shape[:2]
    mask = _foreground_mask(image)
    scale_x = original_width / mask.shape[1]
    scale_y = original_height / mask.shape[0]

    # Remove notebook/table rules before joining characters into word contours.
    clean = _remove_page_rules(mask)

    join_width = max(12, mask.shape[1] // 80)
    joined = cv2.dilate(
        clean,
        cv2.getStructuringElement(cv2.MORPH_RECT, (join_width, 3)),
        iterations=1,
    )
    contours, _ = cv2.findContours(joined, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    min_area = max(12, mask.shape[0] * mask.shape[1] // 500_000)
    boxes: list[tuple[int, int, int, int]] = []
    for contour in contours:
        x, y, width, height = cv2.boundingRect(contour)
        if width * height >= min_area and height >= 3:
            boxes.append(
                (
                    round(x * scale_x),
                    round(y * scale_y),
                    round(width * scale_x),
                    round(height * scale_y),
                )
            )
    contour_regions = _merge_line_boxes(boxes, original_width)
    suspiciously_tall = any(
        region.height > original_height * 0.25 for region in contour_regions
    )
    if suspiciously_tall:
        projection_mask = _remove_page_rules(mask, aggressive=True)
        projection_regions = _projection_line_regions(
            projection_mask, original_width, original_height
        )
        if len(projection_regions) > len(contour_regions):
            return projection_regions
    return contour_regions


def _crop_line(image: np.ndarray, region: LineRegion) -> np.ndarray:
    page_height, page_width = image.shape[:2]
    pad_x = max(4, region.height // 3)
    pad_y = max(3, region.height // 5)
    left, top = max(0, region.x - pad_x), max(0, region.y - pad_y)
    right = min(page_width, region.x + region.width + pad_x)
    bottom = min(page_height, region.y + region.height + pad_y)
    return image[top:bottom, left:right]


def _prepare_handwritten_crop(line_image: np.ndarray) -> np.ndarray:
    """Suppress ruled-paper backgrounds and tightly crop dark handwriting."""
    gray = (
        cv2.cvtColor(line_image, cv2.COLOR_BGR2GRAY)
        if line_image.ndim == 3
        else line_image
    )
    blurred = cv2.GaussianBlur(gray, (3, 3), 0)
    otsu_threshold, _ = cv2.threshold(
        blurred, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU
    )
    ink_threshold = int(np.clip(otsu_threshold * 0.7, 75, 125))
    ink = cv2.threshold(gray, ink_threshold, 255, cv2.THRESH_BINARY_INV)[1]

    horizontal = cv2.morphologyEx(
        ink,
        cv2.MORPH_OPEN,
        cv2.getStructuringElement(cv2.MORPH_RECT, (max(20, ink.shape[1] // 8), 1)),
    )
    vertical = cv2.morphologyEx(
        ink,
        cv2.MORPH_OPEN,
        cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(12, ink.shape[0] // 2))),
    )
    ink = cv2.subtract(ink, cv2.bitwise_or(horizontal, vertical))

    count, labels, stats, _ = cv2.connectedComponentsWithStats(ink, 8)
    cleaned = np.zeros_like(ink)
    for index in range(1, count):
        if stats[index, cv2.CC_STAT_AREA] >= 4:
            cleaned[labels == index] = 255

    _, points_x = np.where(cleaned > 0)
    if points_x.size:
        left = max(0, int(np.percentile(points_x, 1)) - 10)
        right = min(cleaned.shape[1], int(np.percentile(points_x, 99)) + 11)
        cleaned = cleaned[:, left:right]
    return cv2.cvtColor(255 - cleaned, cv2.COLOR_GRAY2BGR)


def _printed_ocr(line_image: np.ndarray) -> tuple[str, float]:
    """Run fast single-line Tesseract OCR for mixed-page routing."""
    if pytesseract is None:
        return "", 0.0
    try:
        data = pytesseract.image_to_data(
            line_image,
            lang="eng",
            config="--oem 1 --psm 7",
            output_type=Output.DICT,
        )
    except (TesseractError, TesseractNotFoundError):
        return "", 0.0
    words, scores = [], []
    for text, raw_score in zip(data["text"], data["conf"]):
        text = text.strip()
        score = float(raw_score)
        if text and score > 0:
            words.append(text)
            scores.append(score / 100)
    return " ".join(words), sum(scores) / len(scores) if scores else 0.0


def _print_regularity(line_image: np.ndarray) -> float:
    """Estimate how strongly glyphs resemble a regular typeset baseline."""
    mask = _foreground_mask(line_image)
    count, _, stats, centroids = cv2.connectedComponentsWithStats(mask, 8)
    components = [
        (stats[index], centroids[index])
        for index in range(1, count)
        if stats[index, cv2.CC_STAT_AREA] >= 3 and stats[index, cv2.CC_STAT_HEIGHT] >= 3
    ]
    if len(components) < 3:
        return 0.0
    median_height = float(
        np.median([item[0][cv2.CC_STAT_HEIGHT] for item in components])
    )
    components = [
        item
        for item in components
        if item[0][cv2.CC_STAT_HEIGHT] >= max(3, median_height * 0.45)
    ]
    if len(components) < 3:
        return 0.0
    heights = np.array(
        [item[0][cv2.CC_STAT_HEIGHT] for item in components], dtype=float
    )
    bottoms = np.array(
        [item[0][cv2.CC_STAT_TOP] + item[0][cv2.CC_STAT_HEIGHT] for item in components],
        dtype=float,
    )
    height_score = max(0.0, 1.0 - float(np.std(heights) / (np.mean(heights) + 1e-6)))
    baseline_score = max(0.0, 1.0 - float(np.std(bottoms) / (np.mean(heights) + 1e-6)))
    return (height_score + baseline_score) / 2


def classify_text_line(
    line_image: np.ndarray, printed_confidence: float | None = None
) -> LineType:
    """Classify a line as printed or handwritten for mixed-page handling."""
    if printed_confidence is None:
        _, printed_confidence = _printed_ocr(line_image)
    regularity = _print_regularity(line_image)
    return (
        "printed"
        if printed_confidence >= 0.82 and regularity >= 0.82
        else "handwritten"
    )


def _generation_confidences(output: Any, batch_size: int) -> list[float]:
    """Convert generation token logits to one mean probability per line."""
    scores = getattr(output, "scores", None)
    if not scores:
        return [0.0] * batch_size
    try:
        import torch

        token_probabilities = torch.stack(
            [
                torch.softmax(score.detach().float(), dim=-1).max(dim=-1).values
                for score in scores
            ],
            dim=1,
        )
        return [
            float(value)
            for value in token_probabilities.mean(dim=1).clamp(0, 1).tolist()
        ]
    except (ImportError, AttributeError, RuntimeError, TypeError):
        return [0.0] * batch_size


def recognize_handwritten_lines(
    line_images: list[np.ndarray], batch_size: int = 8
) -> list[tuple[str, float]]:
    """Recognize line crops in CPU-friendly batches."""
    if batch_size < 1:
        raise ValueError("batch_size must be at least 1")
    if not line_images:
        return []
    import torch

    processor, model = get_trocr_model()
    results: list[tuple[str, float]] = []
    for start in range(0, len(line_images), batch_size):
        batch = line_images[start : start + batch_size]
        pil_images = []
        for line_image in batch:
            prepared = _prepare_handwritten_crop(line_image)
            rgb = cv2.cvtColor(prepared, cv2.COLOR_BGR2RGB)
            pil_images.append(Image.fromarray(rgb))
        pixel_values = processor(
            images=pil_images, return_tensors="pt"
        ).pixel_values.to("cpu")
        with torch.inference_mode():
            output = model.generate(
                pixel_values,
                max_new_tokens=128,
                return_dict_in_generate=True,
                output_scores=True,
            )
        texts = [
            text.strip()
            for text in processor.batch_decode(
                output.sequences, skip_special_tokens=True
            )
        ]
        confidences = _generation_confidences(output, len(batch))
        results.extend(zip(texts, confidences))
    return results


def recognize_handwritten_line(line_image: np.ndarray) -> tuple[str, float]:
    """Recognize one cropped line with TrOCR and return text/confidence."""
    return recognize_handwritten_lines([line_image], batch_size=1)[0]


def extract_text_handwritten(
    image_path: str,
    confidence_threshold: float | None = None,
    detect_mixed: bool = True,
) -> HandwrittenOCRResult:
    """Load a page and extract ordered handwritten or mixed text lines."""
    image = cv2.imread(os.fspath(image_path))
    if image is None:
        raise ValueError(f"Could not read image from {image_path}")
    return extract_text_handwritten_image(
        image,
        confidence_threshold=confidence_threshold,
        detect_mixed=detect_mixed,
    )


def extract_text_handwritten_image(
    image: np.ndarray,
    confidence_threshold: float | None = None,
    detect_mixed: bool = True,
    deskew_page: bool = True,
) -> HandwrittenOCRResult:
    """Extract ordered text lines from an in-memory handwritten/mixed page."""
    if image is None or image.size == 0:
        raise ValueError("A non-empty image is required for handwritten OCR")
    image = deskew(image) if deskew_page else image
    threshold = (
        settings.ocr_confidence_threshold
        if confidence_threshold is None
        else confidence_threshold
    )
    if not 0 <= threshold <= 1:
        raise ValueError("confidence_threshold must be between 0 and 1")

    prepared_lines: list[tuple[LineRegion, np.ndarray, LineType, str, float]] = []
    for region in segment_text_lines(image):
        crop = _crop_line(image, region)
        printed_text, printed_confidence = (
            _printed_ocr(crop) if detect_mixed else ("", 0.0)
        )
        line_type = (
            classify_text_line(crop, printed_confidence)
            if detect_mixed
            else "handwritten"
        )
        prepared_lines.append(
            (region, crop, line_type, printed_text, printed_confidence)
        )

    handwritten_results = iter(
        recognize_handwritten_lines(
            [
                crop
                for _, crop, line_type, _, _ in prepared_lines
                if line_type == "handwritten"
            ]
        )
    )
    recognized: list[HandwrittenLine] = []
    for region, _, line_type, printed_text, printed_confidence in prepared_lines:
        if line_type == "printed":
            text, confidence = printed_text, printed_confidence
        else:
            text, confidence = next(handwritten_results)
        recognized.append(
            HandwrittenLine(
                **region.model_dump(),
                text=text,
                confidence=max(0.0, min(1.0, confidence)),
                line_type=line_type,
                needs_correction=confidence < threshold,
            )
        )

    kinds = {line.line_type for line in recognized}
    page_type: PageType
    if not kinds:
        page_type = "empty"
    elif len(kinds) == 2:
        page_type = "mixed"
    else:
        page_type = next(iter(kinds))
    confidence = (
        sum(line.confidence for line in recognized) / len(recognized)
        if recognized
        else 0.0
    )
    return HandwrittenOCRResult(
        text="\n".join(line.text for line in recognized),
        lines=recognized,
        confidence=confidence,
        page_type=page_type,
        engine=(
            "trocr+tesseract"
            if page_type == "mixed"
            else "tesseract" if page_type == "printed" else "trocr"
        ),
    )


def _main() -> int:
    parser = argparse.ArgumentParser(description="Recognize handwritten page text")
    parser.add_argument("--input", required=True, help="Path to an input page image")
    parser.add_argument(
        "--no-mixed-detection",
        action="store_true",
        help="Send every detected line to TrOCR",
    )
    args = parser.parse_args()
    try:
        result = extract_text_handwritten(
            args.input, detect_mixed=not args.no_mixed_detection
        )
    except (ValueError, RuntimeError) as exc:
        parser.error(str(exc))
    print(
        f"Page type: {result.page_type}; lines: {len(result.lines)}; "
        f"confidence: {result.confidence:.2f}"
    )
    for line in result.lines:
        flag = " [CHECK]" if line.needs_correction else ""
        print(f"[{line.confidence:.2f}] ({line.line_type}) {line.text}{flag}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
