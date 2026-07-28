#!/usr/bin/env python3
"""Run reproducible, unmocked TrOCR and pix2tex CPU smoke benchmarks."""

from __future__ import annotations

import argparse
import json
import platform
import tempfile
from pathlib import Path
from time import perf_counter

import cv2
import numpy as np
import torch
from PIL import Image, ImageDraw, ImageFont

from src.config.settings import settings
from src.cv import math_extractor, ocr_handwritten

DEFAULT_HANDWRITING_FONT = Path(
    "/System/Library/Fonts/Supplemental/Bradley Hand Bold.ttf"
)
FALLBACK_FONT = "DejaVuSans.ttf"
HANDWRITING_LINES = [
    "The quick brown fox jumps",
    "Exam answers need clear writing",
    "Students solve every question",
]


def _font(font_path: str | None, size: int) -> ImageFont.FreeTypeFont:
    selected = Path(font_path) if font_path else DEFAULT_HANDWRITING_FONT
    if selected.exists():
        return ImageFont.truetype(str(selected), size)
    return ImageFont.truetype(FALLBACK_FONT, size)


def _make_handwriting_fixture(path: Path, font_path: str | None) -> None:
    font = _font(font_path, 46)
    page = Image.new("RGB", (1000, 300), "white")
    drawing = ImageDraw.Draw(page)
    for index, text in enumerate(HANDWRITING_LINES):
        drawing.text((30, 15 + index * 90), text, font=font, fill="black")
    page.save(path)


def _make_equation_fixture() -> np.ndarray:
    page = np.full((90, 500, 3), 255, dtype=np.uint8)
    cv2.putText(
        page,
        "x^2 + y^2 = r^2",
        (15, 60),
        cv2.FONT_HERSHEY_SIMPLEX,
        1.4,
        (0, 0, 0),
        2,
        cv2.LINE_AA,
    )
    return page


def _character_accuracy(expected: str, actual: str) -> float:
    """Return one minus normalized Levenshtein character error rate."""
    normalized_expected = " ".join(expected.lower().split())
    normalized_actual = " ".join(actual.lower().split())
    previous = list(range(len(normalized_actual) + 1))
    for expected_index, expected_character in enumerate(normalized_expected, start=1):
        current = [expected_index]
        for actual_index, actual_character in enumerate(normalized_actual, start=1):
            current.append(
                min(
                    current[-1] + 1,
                    previous[actual_index] + 1,
                    previous[actual_index - 1]
                    + (expected_character != actual_character),
                )
            )
        previous = current
    distance = previous[-1]
    return max(0.0, 1.0 - distance / max(1, len(normalized_expected)))


def run_benchmark(font_path: str | None = None) -> dict[str, object]:
    """Run model initialization once and report warm CPU inference separately."""
    with tempfile.TemporaryDirectory(prefix="examlens-cpu-benchmark-") as directory:
        fixture = Path(directory) / "clean_handwriting.png"
        _make_handwriting_fixture(fixture, font_path)

        cold_started = perf_counter()
        first_ocr = ocr_handwritten.extract_text_handwritten(
            str(fixture), detect_mixed=False
        )
        trocr_cold_seconds = perf_counter() - cold_started

        warm_started = perf_counter()
        ocr_result = ocr_handwritten.extract_text_handwritten(
            str(fixture), detect_mixed=False
        )
        trocr_warm_seconds = perf_counter() - warm_started

        equation_fixture = _make_equation_fixture()
        pix2tex_cold_started = perf_counter()
        math_extractor.recognize_equation(equation_fixture)
        pix2tex_cold_seconds = perf_counter() - pix2tex_cold_started

        pix2tex_warm_started = perf_counter()
        latex, latex_confidence = math_extractor.recognize_equation(equation_fixture)
        pix2tex_warm_seconds = perf_counter() - pix2tex_warm_started

    expected_text = "\n".join(HANDWRITING_LINES)
    return {
        "environment": {
            "platform": platform.platform(),
            "python": platform.python_version(),
            "torch": torch.__version__,
            "device": "cpu",
        },
        "trocr": {
            "model": settings.trocr_model,
            "first_run_seconds_including_model_load": round(trocr_cold_seconds, 3),
            "warm_page_seconds": round(trocr_warm_seconds, 3),
            "character_accuracy": round(
                _character_accuracy(expected_text, ocr_result.text), 4
            ),
            "expected": expected_text,
            "actual": ocr_result.text,
            "lines_detected": len(ocr_result.lines),
            "model_device": str(next(ocr_handwritten._trocr_model.parameters()).device),
            "first_run_actual": first_ocr.text,
        },
        "pix2tex": {
            "first_run_seconds_including_model_load": round(pix2tex_cold_seconds, 3),
            "warm_equation_seconds": round(pix2tex_warm_seconds, 3),
            "latex": latex,
            "confidence": round(latex_confidence, 4),
            "model_device": str(math_extractor._latex_model.args.device),
        },
    }


def _main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--font",
        help="Optional TrueType/OpenType handwriting font for the generated fixture",
    )
    parser.add_argument(
        "--assert-targets",
        action="store_true",
        help="Exit non-zero unless OCR accuracy >80%% and warm time <15 sec/page",
    )
    args = parser.parse_args()
    result = run_benchmark(args.font)
    print(json.dumps(result, indent=2))
    if args.assert_targets:
        trocr = result["trocr"]
        if trocr["character_accuracy"] <= 0.8 or trocr["warm_page_seconds"] >= 15:
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
