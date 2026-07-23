import sys
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import cv2
import numpy as np

from src.cv import ocr_handwritten
from src.cv.ocr_handwritten import (
    HandwrittenOCRResult,
    LineRegion,
    extract_text_handwritten,
    segment_text_lines,
)


def _page() -> np.ndarray:
    image = np.full((220, 600, 3), 255, dtype=np.uint8)
    cv2.putText(image, "First handwritten line", (30, 65), 0, 1.0, (0, 0, 0), 2)
    cv2.putText(image, "Second handwritten line", (30, 145), 0, 1.0, (0, 0, 0), 2)
    return image


def test_line_segmentation_detects_clean_handwriting():
    lines = segment_text_lines(_page())
    assert len(lines) == 2
    assert lines[0].y < lines[1].y
    assert all(line.width > 200 and line.height > 15 for line in lines)


def test_trocr_model_loads_on_cpu_and_is_cached(monkeypatch):
    processor = MagicMock()
    model = MagicMock()
    processor_class = MagicMock()
    model_class = MagicMock()
    processor_class.from_pretrained.return_value = processor
    model_class.from_pretrained.return_value = model
    fake_transformers = SimpleNamespace(
        TrOCRProcessor=processor_class,
        VisionEncoderDecoderModel=model_class,
    )
    monkeypatch.setitem(sys.modules, "transformers", fake_transformers)
    monkeypatch.setattr(ocr_handwritten, "_trocr_processor", None)
    monkeypatch.setattr(ocr_handwritten, "_trocr_model", None)
    monkeypatch.setattr(ocr_handwritten, "_trocr_model_name", None)

    first = ocr_handwritten.get_trocr_model("test/trocr")
    second = ocr_handwritten.get_trocr_model("test/trocr")

    assert first == second == (processor, model)
    processor_class.from_pretrained.assert_called_once_with("test/trocr")
    model_class.from_pretrained.assert_called_once_with("test/trocr")
    model.to.assert_called_once_with("cpu")
    model.eval.assert_called_once_with()


@patch("src.cv.ocr_handwritten.cv2.imread")
@patch("src.cv.ocr_handwritten.recognize_handwritten_lines")
@patch("src.cv.ocr_handwritten._printed_ocr", return_value=("", 0.0))
def test_clean_handwriting_is_recognized_line_by_line(
    mock_printed, mock_recognize, mock_imread
):
    mock_imread.return_value = _page()
    mock_recognize.return_value = [
        ("First handwritten line", 0.94),
        ("Second handwritten line", 0.91),
    ]

    result = extract_text_handwritten("clean.png")

    assert isinstance(result, HandwrittenOCRResult)
    assert result.page_type == "handwritten"
    assert result.text == "First handwritten line\nSecond handwritten line"
    assert len(result.lines) == 2
    assert all(not line.needs_correction for line in result.lines)
    mock_recognize.assert_called_once()
    assert len(mock_recognize.call_args.args[0]) == 2


@patch("src.cv.ocr_handwritten.cv2.imread")
@patch(
    "src.cv.ocr_handwritten.segment_text_lines",
    return_value=[LineRegion(x=10, y=20, width=300, height=35)],
)
@patch("src.cv.ocr_handwritten.recognize_handwritten_lines")
@patch("src.cv.ocr_handwritten._printed_ocr", return_value=("", 0.0))
def test_messy_handwriting_is_flagged_for_correction(
    mock_printed, mock_recognize, mock_segment, mock_imread
):
    mock_imread.return_value = _page()
    mock_recognize.return_value = [("uncertain answer", 0.41)]

    result = extract_text_handwritten("messy.png")

    assert result.lines[0].confidence == 0.41
    assert result.lines[0].needs_correction is True


@patch("src.cv.ocr_handwritten.cv2.imread")
@patch(
    "src.cv.ocr_handwritten.segment_text_lines",
    return_value=[LineRegion(x=10, y=20, width=300, height=35)],
)
@patch("src.cv.ocr_handwritten.recognize_handwritten_lines")
@patch("src.cv.ocr_handwritten._printed_ocr", return_value=("", 0.0))
def test_unreadable_line_is_retained_for_manual_correction(
    mock_printed, mock_recognize, mock_segment, mock_imread
):
    mock_imread.return_value = _page()
    mock_recognize.return_value = [("", 0.0)]

    result = extract_text_handwritten("unreadable.png")

    assert len(result.lines) == 1
    assert result.lines[0].text == ""
    assert result.lines[0].needs_correction is True
    assert result.page_type == "handwritten"


@patch("src.cv.ocr_handwritten.cv2.imread")
@patch(
    "src.cv.ocr_handwritten.segment_text_lines",
    return_value=[
        LineRegion(x=10, y=10, width=300, height=30),
        LineRegion(x=10, y=70, width=300, height=30),
    ],
)
@patch(
    "src.cv.ocr_handwritten.classify_text_line",
    side_effect=["printed", "handwritten"],
)
@patch("src.cv.ocr_handwritten.recognize_handwritten_lines")
@patch("src.cv.ocr_handwritten._printed_ocr")
def test_mixed_page_routes_printed_and_handwritten_lines(
    mock_printed, mock_recognize, mock_classify, mock_segment, mock_imread
):
    mock_imread.return_value = _page()
    mock_printed.side_effect = [("UNIVERSITY EXAM", 0.97), ("rough answer", 0.30)]
    mock_recognize.return_value = [("The handwritten answer", 0.89)]

    result = extract_text_handwritten("mixed.png")

    assert result.page_type == "mixed"
    assert result.engine == "trocr+tesseract"
    assert [line.line_type for line in result.lines] == ["printed", "handwritten"]
    assert result.text == "UNIVERSITY EXAM\nThe handwritten answer"
    mock_recognize.assert_called_once()
