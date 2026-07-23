"""Confidence-aware printed OCR using Tesseract with an EasyOCR fallback."""

import re
from typing import Any

import cv2
import easyocr
import numpy as np
import pytesseract
from pydantic import BaseModel
from pytesseract import Output, TesseractError, TesseractNotFoundError

from src.config.settings import settings
from src.cv.preprocessing import preprocess_image

TESSERACT_CONFIG = "--oem 1 --psm 3"
_easyocr_reader = None


class OCRResult(BaseModel):
    text: str
    confidence: float
    engine: str
    bounding_boxes: list[dict[str, Any]]


def get_easyocr_reader():
    """Load the heavier fallback model only when it is actually needed."""
    global _easyocr_reader
    if _easyocr_reader is None:
        _easyocr_reader = easyocr.Reader(["en", "hi"], gpu=False)
    return _easyocr_reader


def post_process_text(text: str) -> str:
    """Correct the milestone's common OCR confusions using local context."""
    text = re.sub(r"(?<=[A-Za-z])rn(?=[A-Za-z]|$)|\brn\b", "m", text)
    text = re.sub(r"(?<=\d)O(?=\d)|(?<=\d)O\b|\bO(?=\d)", "0", text)
    text = re.sub(r"(?<=\d)l(?=\d)|(?<=\d)l\b|\bl(?=\d)", "1", text)
    return text


def tesseract_ocr(image: np.ndarray, lang: str = "eng+hin") -> OCRResult:
    """Run Tesseract LSTM OCR and return text, confidence, and word boxes."""
    data = pytesseract.image_to_data(
        image,
        lang=lang,
        config=TESSERACT_CONFIG,
        output_type=Output.DICT,
    )
    words: list[str] = []
    confidences: list[float] = []
    boxes: list[dict[str, Any]] = []
    for index, raw_text in enumerate(data["text"]):
        word = raw_text.strip()
        confidence = float(data["conf"][index])
        if not word or confidence <= 0:
            continue
        words.append(word)
        confidences.append(confidence)
        boxes.append(
            {
                "x": int(data["left"][index]),
                "y": int(data["top"][index]),
                "w": int(data["width"][index]),
                "h": int(data["height"][index]),
                "text": word,
                "conf": confidence,
            }
        )
    average = sum(confidences) / len(confidences) / 100 if confidences else 0.0
    return OCRResult(
        text=post_process_text(" ".join(words)),
        confidence=average,
        engine="tesseract",
        bounding_boxes=boxes,
    )


def easyocr_fallback(image: np.ndarray) -> OCRResult:
    """Run CPU EasyOCR and normalize its polygon boxes to x/y/w/h boxes."""
    results = get_easyocr_reader().readtext(image)
    words: list[str] = []
    confidences: list[float] = []
    boxes: list[dict[str, Any]] = []
    for polygon, raw_text, probability in results:
        word = raw_text.strip()
        if not word:
            continue
        x_values = [point[0] for point in polygon]
        y_values = [point[1] for point in polygon]
        x, y = min(x_values), min(y_values)
        width, height = max(x_values) - x, max(y_values) - y
        words.append(word)
        confidences.append(float(probability))
        boxes.append(
            {
                "x": int(x),
                "y": int(y),
                "w": int(width),
                "h": int(height),
                "text": word,
                "conf": float(probability),
            }
        )
    average = sum(confidences) / len(confidences) if confidences else 0.0
    return OCRResult(
        text=post_process_text(" ".join(words)),
        confidence=average,
        engine="easyocr",
        bounding_boxes=boxes,
    )


def extract_text_printed(image_path: str, preprocess: bool = True) -> OCRResult:
    """Use fast Tesseract first and return EasyOCR only when it is better."""
    image = cv2.imread(image_path)
    if image is None:
        raise ValueError(f"Could not read image from {image_path}")
    prepared = preprocess_image(image) if preprocess else image

    try:
        primary = tesseract_ocr(prepared)
    except TesseractError:
        # Keep English OCR usable on machines that have not installed the
        # optional Hindi language pack. Docker installs both languages.
        try:
            primary = tesseract_ocr(prepared, lang="eng")
        except (TesseractError, TesseractNotFoundError):
            primary = OCRResult(
                text="", confidence=0.0, engine="tesseract", bounding_boxes=[]
            )
    except TesseractNotFoundError:
        primary = OCRResult(
            text="", confidence=0.0, engine="tesseract", bounding_boxes=[]
        )

    if primary.text and primary.confidence >= settings.ocr_confidence_threshold:
        return primary

    fallback = easyocr_fallback(prepared)
    return fallback if fallback.confidence > primary.confidence else primary
