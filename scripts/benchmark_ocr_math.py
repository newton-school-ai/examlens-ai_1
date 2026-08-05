#!/usr/bin/env python3
"""Run reproducible, unmocked TrOCR and pix2tex CPU smoke benchmarks."""

from __future__ import annotations

import argparse
import json
import platform
import re
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
EXPECTED_EQUATION_LATEX = "x=2"
EXPECTED_INTEGRATED_TEXT = "Use $x=2$ now"

# These merge gates are intentionally stricter than Issues #7 and #8.  The
# issues require >80% clean-handwriting accuracy, <15 seconds/page, and <5
# seconds/equation.  Keeping a small safety margin prevents a borderline local
# pass from turning into a failure on a slightly slower CPU or harder page.
MIN_HANDWRITING_CHARACTER_ACCURACY = 0.85
MAX_HANDWRITING_PAGE_SECONDS = 12.0
MAX_EQUATION_SECONDS = 4.0


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
    """Create a deterministic equation crop that pix2tex recognizes reliably."""
    page = np.full((110, 650, 3), 255, dtype=np.uint8)
    cv2.putText(
        page,
        "x = 2",
        (20, 75),
        cv2.FONT_HERSHEY_SIMPLEX,
        1.8,
        (0, 0, 0),
        3,
        cv2.LINE_AA,
    )
    return page


def _make_mixed_equation_fixture(path: Path) -> None:
    """Create a printed sentence with one inline equation for full-pipeline checks."""
    page = np.full((180, 900, 3), 255, dtype=np.uint8)
    cv2.putText(
        page,
        "Use x = 2 now",
        (25, 105),
        cv2.FONT_HERSHEY_SIMPLEX,
        1.7,
        (0, 0, 0),
        3,
        cv2.LINE_AA,
    )
    if not cv2.imwrite(str(path), page):
        raise RuntimeError(f"Could not write benchmark fixture to {path}")


def normalize_benchmark_latex(latex: str) -> str:
    """Remove presentational wrappers before exact fixture comparison."""
    normalized = re.sub(
        r"\\(?:displaystyle|textstyle|scriptstyle|scriptscriptstyle)\b", "", latex
    )
    previous = None
    while normalized != previous:
        previous = normalized
        normalized = re.sub(
            r"\\(?:mathbf|mathrm|mathit|mathsf|mathtt)\{([^{}]*)\}",
            r"\1",
            normalized,
        )
    normalized = re.sub(r"\\(?:left|right)\b", "", normalized)
    normalized = re.sub(r"\\[,;:!]", "", normalized)
    return re.sub(r"\s+", "", normalized)


def normalize_integrated_math_text(text: str) -> str:
    """Canonicalize inline LaTeX while preserving its surrounding text position."""
    return re.sub(
        r"\$([^$]+)\$",
        lambda match: f"${normalize_benchmark_latex(match.group(1))}$",
        text,
    )


def _character_accuracy(expected: str, actual: str) -> float:
    """Return one minus case-sensitive normalized character error rate."""
    normalized_expected = " ".join(expected.split())
    normalized_actual = " ".join(actual.split())
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


def run_benchmark(
    font_path: str | None = None,
    handwriting_image: str | None = None,
    handwriting_transcript: str | None = None,
) -> dict[str, object]:
    """Run model initialization once and report warm CPU inference separately."""
    if bool(handwriting_image) != bool(handwriting_transcript):
        raise ValueError(
            "handwriting_image and handwriting_transcript must be supplied together"
        )

    with tempfile.TemporaryDirectory(prefix="examlens-cpu-benchmark-") as directory:
        if handwriting_image:
            fixture = Path(handwriting_image)
            transcript_path = Path(handwriting_transcript or "")
            if not fixture.is_file():
                raise ValueError(f"Could not read handwriting image from {fixture}")
            if not transcript_path.is_file():
                raise ValueError(
                    f"Could not read handwriting transcript from {transcript_path}"
                )
            expected_text = transcript_path.read_text(encoding="utf-8").strip()
            fixture_kind = "supplied"
        else:
            fixture = Path(directory) / "clean_handwriting.png"
            _make_handwriting_fixture(fixture, font_path)
            expected_text = "\n".join(HANDWRITING_LINES)
            fixture_kind = "synthetic"

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

        mixed_fixture = Path(directory) / "mixed_text_equation.png"
        _make_mixed_equation_fixture(mixed_fixture)
        integration_started = perf_counter()
        integrated_result = math_extractor.extract_text_with_equations(
            str(mixed_fixture)
        )
        integration_seconds = perf_counter() - integration_started
        canonical_integrated_text = normalize_integrated_math_text(
            integrated_result.text
        )

    return {
        "environment": {
            "platform": platform.platform(),
            "python": platform.python_version(),
            "torch": torch.__version__,
            "device": "cpu",
        },
        "trocr": {
            "model": settings.trocr_model,
            "fixture_kind": fixture_kind,
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
            "expected_latex": EXPECTED_EQUATION_LATEX,
            "latex": latex,
            "canonical_latex": normalize_benchmark_latex(latex),
            "latex_matches_expected": (
                normalize_benchmark_latex(latex) == EXPECTED_EQUATION_LATEX
            ),
            "latex_is_valid": math_extractor.is_valid_latex(latex),
            "confidence": round(latex_confidence, 4),
            "model_device": str(math_extractor._latex_model.args.device),
            "mixed_page_seconds": round(integration_seconds, 3),
            "expected_integrated_text": EXPECTED_INTEGRATED_TEXT,
            "integrated_text": integrated_result.text,
            "canonical_integrated_text": canonical_integrated_text,
            "integrated_text_matches_expected": (
                canonical_integrated_text == EXPECTED_INTEGRATED_TEXT
            ),
            "mixed_page_equations_detected": len(integrated_result.equations),
        },
    }


def _main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--font",
        help="Optional TrueType/OpenType handwriting font for the generated fixture",
    )
    parser.add_argument(
        "--handwriting-image",
        help="Optional real handwriting page; requires --handwriting-transcript",
    )
    parser.add_argument(
        "--handwriting-transcript",
        help="UTF-8 ground-truth text for --handwriting-image",
    )
    parser.add_argument(
        "--assert-targets",
        action="store_true",
        help=(
            "Exit non-zero unless the stricter merge gates pass: OCR accuracy "
            ">85%%, warm time <12 sec/page and <4 sec/equation, and exact math"
        ),
    )
    args = parser.parse_args()
    try:
        result = run_benchmark(
            args.font,
            handwriting_image=args.handwriting_image,
            handwriting_transcript=args.handwriting_transcript,
        )
    except ValueError as exc:
        parser.error(str(exc))
    print(json.dumps(result, indent=2))
    if args.assert_targets:
        trocr = result["trocr"]
        pix2tex = result["pix2tex"]
        if (
            trocr["character_accuracy"] <= MIN_HANDWRITING_CHARACTER_ACCURACY
            or trocr["warm_page_seconds"] >= MAX_HANDWRITING_PAGE_SECONDS
            or pix2tex["warm_equation_seconds"] >= MAX_EQUATION_SECONDS
            or not pix2tex["latex_matches_expected"]
            or not pix2tex["latex_is_valid"]
            or not pix2tex["integrated_text_matches_expected"]
            or pix2tex["mixed_page_equations_detected"] != 1
        ):
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
