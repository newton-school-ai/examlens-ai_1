"""Printed text OCR using Tesseract and EasyOCR."""
# isort: skip_file

import re
from typing import Any, Dict, List

import cv2
import easyocr
import pytesseract
from pydantic import BaseModel
from pytesseract import Output

# Initialize EasyOCR reader lazily to avoid loading models if not needed
_easyocr_reader = None


def get_easyocr_reader():
    global _easyocr_reader
    if _easyocr_reader is None:
        _easyocr_reader = easyocr.Reader(["en", "hi"])
    return _easyocr_reader


class OCRResult(BaseModel):
    text: str
    confidence: float
    engine: str
    bounding_boxes: List[Dict[str, Any]]


def post_process_text(text: str) -> str:
    """
    Corrects common OCR errors based on simple heuristics.
    Issue 6 specific replacements:
    'l' -> '1' (in digit context)
    'O' -> '0' (in digit context)
    'rn' -> 'm'
    """
    # Replace 'rn' with 'm' (naive replace as per issue description)
    text = text.replace("rn", "m")

    # Context-aware replacement for 'O' -> '0'
    text = re.sub(r"(?<=\d)O", "0", text)
    text = re.sub(r"O(?=\d)", "0", text)

    # Context-aware replacement for 'l' -> '1'
    text = re.sub(r"(?<=\d)l", "1", text)
    text = re.sub(r"l(?=\d)", "1", text)

    return text


def extract_text_printed(image_path: str) -> OCRResult:
    """
    Extract printed text from an image using Tesseract (primary) and EasyOCR (fallback).
    """
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError(f"Could not read image from {image_path}")

    # 1. Try Tesseract first
    try:
        data = pytesseract.image_to_data(img, lang="eng+hin", output_type=Output.DICT)

        text_parts = []
        confidences = []
        bboxes = []

        for i in range(len(data["text"])):
            text = data["text"][i].strip()
            conf = float(data["conf"][i])
            if text and conf > 0:  # Valid word with confidence
                text_parts.append(text)
                confidences.append(conf)
                bboxes.append(
                    {
                        "x": data["left"][i],
                        "y": data["top"][i],
                        "w": data["width"][i],
                        "h": data["height"][i],
                        "text": text,
                        "conf": conf,
                    }
                )

        overall_conf = (
            (sum(confidences) / len(confidences) / 100.0) if confidences else 0.0
        )

        if overall_conf >= 0.7 and text_parts:
            # Tesseract succeeded with high confidence
            full_text = " ".join(text_parts)
            processed_text = post_process_text(full_text)
            return OCRResult(
                text=processed_text,
                confidence=overall_conf,
                engine="tesseract",
                bounding_boxes=bboxes,
            )

    except Exception:
        # Fallback if tesseract fails completely
        pass

    # 2. EasyOCR Fallback (if tesseract conf < 0.7 or failed)
    reader = get_easyocr_reader()
    results = reader.readtext(image_path)

    text_parts = []
    confidences = []
    bboxes = []

    for bbox, text, prob in results:
        text = text.strip()
        if text:
            text_parts.append(text)
            confidences.append(prob)

            x_coords = [p[0] for p in bbox]
            y_coords = [p[1] for p in bbox]
            x, y = min(x_coords), min(y_coords)
            w, h = max(x_coords) - x, max(y_coords) - y

            bboxes.append(
                {
                    "x": int(x),
                    "y": int(y),
                    "w": int(w),
                    "h": int(h),
                    "text": text,
                    "conf": float(prob),
                }
            )

    overall_conf = (sum(confidences) / len(confidences)) if confidences else 0.0
    full_text = " ".join(text_parts)
    processed_text = post_process_text(full_text)

    return OCRResult(
        text=processed_text,
        confidence=overall_conf,
        engine="easyocr",
        bounding_boxes=bboxes,
    )
