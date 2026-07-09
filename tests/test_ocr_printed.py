# isort: skip_file
from unittest.mock import MagicMock, patch

import pytest

from src.cv.ocr_printed import OCRResult, extract_text_printed, post_process_text


@pytest.fixture
def mock_cv2_imread():
    with patch("src.cv.ocr_printed.cv2.imread") as mock_imread:
        mock_imread.return_value = MagicMock()  # Mock image array
        yield mock_imread


@patch("src.cv.ocr_printed.pytesseract.image_to_data")
@patch("src.cv.ocr_printed.get_easyocr_reader")
def test_clean_scan_uses_tesseract(mock_get_reader, mock_tesseract, mock_cv2_imread):
    # Mock high confidence tesseract result
    mock_tesseract.return_value = {
        "text": ["Hello", "World", ""],
        "conf": ["95", "90", "-1"],
        "left": [10, 50, 0],
        "top": [10, 10, 0],
        "width": [30, 40, 0],
        "height": [15, 15, 0],
    }

    result = extract_text_printed("dummy_path.png")

    assert result.engine == "tesseract"
    assert result.confidence == 0.925  # (95+90)/2 / 100
    assert result.text == "Hello World"
    mock_get_reader.assert_not_called()  # EasyOCR shouldn't be loaded/called


@patch("src.cv.ocr_printed.pytesseract.image_to_data")
@patch("src.cv.ocr_printed.get_easyocr_reader")
def test_noisy_scan_triggers_easyocr_fallback(
    mock_get_reader, mock_tesseract, mock_cv2_imread
):
    # Mock low confidence tesseract result (< 70%)
    mock_tesseract.return_value = {
        "text": ["H3llo", "W0rld", ""],
        "conf": ["50", "60", "-1"],
        "left": [10, 50, 0],
        "top": [10, 10, 0],
        "width": [30, 40, 0],
        "height": [15, 15, 0],
    }

    mock_reader = MagicMock()
    # EasyOCR returns [[bbox, text, confidence], ...]
    mock_reader.readtext.return_value = [
        ([[10, 10], [40, 10], [40, 25], [10, 25]], "Hello", 0.85),
        ([[50, 10], [90, 10], [90, 25], [50, 25]], "World", 0.90),
    ]
    mock_get_reader.return_value = mock_reader

    result = extract_text_printed("dummy_path.png")

    assert result.engine == "easyocr"
    assert result.confidence == 0.875  # (0.85+0.90)/2
    assert result.text == "Hello World"
    mock_reader.readtext.assert_called_once_with("dummy_path.png")


@patch("src.cv.ocr_printed.pytesseract.image_to_data")
@patch("src.cv.ocr_printed.get_easyocr_reader")
def test_hindi_text_extraction(mock_get_reader, mock_tesseract, mock_cv2_imread):
    mock_tesseract.return_value = {
        "text": ["नमस्ते", "दुनिया", ""],
        "conf": ["90", "95", "-1"],
        "left": [10, 50, 0],
        "top": [10, 10, 0],
        "width": [30, 40, 0],
        "height": [15, 15, 0],
    }

    result = extract_text_printed("dummy_path.png")

    assert result.engine == "tesseract"
    assert result.text == "नमस्ते दुनिया"


def test_post_processing():
    # Test 'rn' to 'm'
    assert post_process_text("bom") == "bom"
    assert post_process_text("born") == "bom"
    assert post_process_text("modem") == "modem"
    assert post_process_text("modem rn") == "modem m"

    # Test 'O' to '0' in digit context
    assert post_process_text("12O45") == "12045"
    assert post_process_text("O123") == "0123"
    assert post_process_text("45O") == "450"
    assert post_process_text("Open") == "Open"
    assert post_process_text("Hello") == "Hello"

    # Test 'l' to '1' in digit context
    assert post_process_text("12l45") == "12145"
    assert post_process_text("l123") == "1123"
    assert post_process_text("45l") == "451"
    assert post_process_text("list") == "list"


@patch("src.cv.ocr_printed.pytesseract.image_to_data")
def test_structured_output_format(mock_tesseract, mock_cv2_imread):
    mock_tesseract.return_value = {
        "text": ["Data"],
        "conf": ["99"],
        "left": [10],
        "top": [10],
        "width": [30],
        "height": [15],
    }

    result = extract_text_printed("dummy_path.png")

    assert isinstance(result, OCRResult)
    assert hasattr(result, "text")
    assert hasattr(result, "confidence")
    assert hasattr(result, "engine")
    assert hasattr(result, "bounding_boxes")

    bbox = result.bounding_boxes[0]
    assert bbox["x"] == 10
    assert bbox["y"] == 10
    assert bbox["w"] == 30
    assert bbox["h"] == 15
    assert bbox["text"] == "Data"
    assert bbox["conf"] == 99.0
