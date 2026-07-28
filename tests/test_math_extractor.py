from unittest.mock import patch

import numpy as np
import pytest

from src.cv.math_extractor import (
    MATH_TOKEN,
    EquationRegion,
    EquationResult,
    detect_equation_regions,
    extract_equations,
    extract_text_with_equations,
    is_valid_latex,
    merge_equations_into_text,
    normalize_latex,
    recognize_equation,
)
from src.cv.ocr_handwritten import HandwrittenLine, HandwrittenOCRResult


@pytest.fixture
def mock_page():
    with patch("src.cv.math_extractor.cv2.imread") as imread:
        imread.return_value = np.full((500, 700, 3), 255, dtype=np.uint8)
        yield imread


@pytest.mark.parametrize(
    ("latex", "box"),
    [
        (r"x^2 + y^2 = r^2", (20, 30, 220, 45)),
        (r"\int_0^\infty e^{-x}\,dx = 1", (20, 100, 300, 70)),
        (
            r"\begin{bmatrix}1 & 2 \\ 3 & 4\end{bmatrix}",
            (30, 190, 240, 110),
        ),
    ],
    ids=["simple-equation", "complex-integral", "matrix"],
)
@patch("src.cv.math_extractor.recognize_equation")
@patch("src.cv.math_extractor.detect_equation_regions")
def test_extracts_display_equations(mock_detect, mock_recognize, mock_page, latex, box):
    x, y, width, height = box
    mock_detect.return_value = [
        EquationRegion(
            x=x,
            y=y,
            width=width,
            height=height,
            detection_confidence=0.9,
        )
    ]
    mock_recognize.return_value = (latex, 0.92)

    results = extract_equations("math.png")

    assert len(results) == 1
    assert results[0].latex == latex
    assert results[0].x == x
    assert results[0].y == y
    assert results[0].confidence > 0.9
    assert results[0].needs_correction is False


@patch("src.cv.math_extractor.recognize_equation")
@patch("src.cv.math_extractor.detect_equation_regions")
def test_extracts_inline_math_in_page_order(mock_detect, mock_recognize, mock_page):
    mock_detect.return_value = [
        EquationRegion(
            x=180,
            y=50,
            width=90,
            height=25,
            detection_confidence=0.88,
            inline=True,
        )
    ]
    mock_recognize.return_value = (r"E=mc^2", 0.95)

    result = extract_equations("inline.png")[0]

    assert result.inline is True
    assert result.latex == r"E=mc^2"


def test_embeds_inline_and_display_latex_at_page_coordinates():
    lines = [
        HandwrittenLine(
            x=20,
            y=20,
            width=400,
            height=35,
            text="The value is valid",
            confidence=0.9,
        ),
        HandwrittenLine(
            x=20,
            y=180,
            width=400,
            height=35,
            text="Therefore the proof is complete",
            confidence=0.9,
        ),
    ]
    equations = [
        EquationResult(
            x=257,
            y=22,
            width=60,
            height=30,
            detection_confidence=0.9,
            inline=True,
            latex=r"x^2",
            confidence=0.9,
        ),
        EquationResult(
            x=100,
            y=100,
            width=220,
            height=55,
            detection_confidence=0.9,
            latex=r"\frac{a}{b}",
            confidence=0.9,
        ),
    ]

    text = merge_equations_into_text(lines, equations)

    assert text == (
        "The value is $x^2$ valid\n"
        r"$$\frac{a}{b}$$"
        "\nTherefore the proof is complete"
    )


@patch("src.cv.math_extractor.extract_equations")
@patch("src.cv.ocr_handwritten.extract_text_handwritten_image")
@patch("src.cv.math_extractor.cv2.imread")
def test_page_extraction_masks_math_and_returns_integrated_text(
    mock_imread, mock_text, mock_equations
):
    mock_imread.return_value = np.zeros((100, 400, 3), dtype=np.uint8)
    line = HandwrittenLine(
        x=10,
        y=10,
        width=300,
        height=30,
        text="Use identity here",
        confidence=0.88,
    )
    mock_text.return_value = HandwrittenOCRResult(
        text=line.text,
        lines=[line],
        confidence=0.88,
        page_type="handwritten",
        engine="trocr",
    )
    mock_equations.return_value = [
        EquationResult(
            x=105,
            y=12,
            width=45,
            height=24,
            detection_confidence=0.9,
            inline=True,
            latex=r"a^2+b^2",
            confidence=0.9,
        )
    ]

    result = extract_text_with_equations("page.png")

    assert result.text == r"Use $a^2+b^2$ identity here"
    assert result.text_confidence == 0.88
    assert result.equations[0].latex == r"a^2+b^2"
    masked_image = mock_text.call_args.args[0]
    assert np.all(masked_image[10:38, 103:152] == 255)
    assert np.all(masked_image[:, :100] == 0)
    assert mock_text.call_args.kwargs["deskew_page"] is False


def test_latex_normalization_and_validation_are_katex_friendly():
    assert normalize_latex(r"$$ \displaystyle \frac{a}{b} $$") == r"\frac{a}{b}"
    assert is_valid_latex(r"\sum_{i=1}^{n} i")
    assert is_valid_latex(r"\begin{matrix}a & b \\ c & d\end{matrix}")
    assert not is_valid_latex(r"\frac{a}{b")


@pytest.mark.parametrize("token", ["sin", "lim", "3/4", "x^2", "a=b"])
def test_math_token_pattern_recognizes_textual_and_symbolic_math(token):
    assert MATH_TOKEN.search(token)


@patch("src.cv.math_extractor.get_latex_model")
def test_recognizer_preserves_an_explicit_zero_model_confidence(mock_get_model):
    mock_get_model.return_value.return_value = {
        "latex": r"x=1",
        "confidence": 0.0,
    }

    latex, confidence = recognize_equation(np.full((30, 80, 3), 255, dtype=np.uint8))

    assert latex == r"x=1"
    assert confidence == 0.0


def test_visual_detector_groups_a_stacked_fraction():
    import cv2

    page = np.full((240, 500, 3), 255, dtype=np.uint8)
    cv2.putText(page, "x+1", (170, 85), 0, 0.9, (0, 0, 0), 2)
    cv2.line(page, (155, 100), (250, 100), (0, 0, 0), 2)
    cv2.putText(page, "x-1", (170, 140), 0, 0.9, (0, 0, 0), 2)

    regions = detect_equation_regions(page)

    assert any(
        region.x <= 170
        and region.y <= 70
        and region.x + region.width >= 225
        and region.y + region.height >= 135
        for region in regions
    )


def test_visual_detector_groups_a_matrix():
    import cv2

    page = np.full((240, 500, 3), 255, dtype=np.uint8)
    cv2.line(page, (140, 55), (140, 160), (0, 0, 0), 3)
    cv2.line(page, (140, 55), (160, 55), (0, 0, 0), 3)
    cv2.line(page, (140, 160), (160, 160), (0, 0, 0), 3)
    cv2.line(page, (300, 55), (300, 160), (0, 0, 0), 3)
    cv2.line(page, (280, 55), (300, 55), (0, 0, 0), 3)
    cv2.line(page, (280, 160), (300, 160), (0, 0, 0), 3)
    for x, y, value in [
        (180, 95, "1"),
        (240, 95, "2"),
        (180, 145, "3"),
        (240, 145, "4"),
    ]:
        cv2.putText(page, value, (x, y), 0, 1.0, (0, 0, 0), 2)

    regions = detect_equation_regions(page)

    assert any(
        region.x <= 140
        and region.y <= 55
        and region.x + region.width >= 300
        and region.y + region.height >= 160
        for region in regions
    )


@patch("src.cv.math_extractor._line_regions", return_value=[])
@patch("src.cv.math_extractor._structural_math_regions", return_value=[])
@patch("src.cv.math_extractor._ocr_math_regions")
def test_detection_threshold_applies_to_every_detector(
    mock_ocr, mock_structural, mock_lines
):
    mock_ocr.return_value = [
        EquationRegion(
            x=10,
            y=20,
            width=100,
            height=30,
            detection_confidence=0.6,
        )
    ]
    page = np.full((100, 200, 3), 255, dtype=np.uint8)

    assert detect_equation_regions(page, min_confidence=0.8) == []


@patch("src.cv.math_extractor.recognize_equation")
@patch("src.cv.math_extractor.detect_equation_regions")
def test_low_confidence_equation_is_flagged(mock_detect, mock_recognize, mock_page):
    mock_detect.return_value = [
        EquationRegion(x=10, y=20, width=100, height=30, detection_confidence=0.5)
    ]
    mock_recognize.return_value = (r"x + ?", 0.4)

    result = extract_equations("unclear.png")[0]

    assert result.needs_correction is True
    assert 0 <= result.confidence <= 1
