import time

import cv2
import numpy as np
import pytest

from src.cv.preprocessing import (
    apply_clahe,
    binarize,
    denoise,
    deskew,
    preprocess_image,
)


def create_synthetic_image():
    """Create a white image with a black rectangle (simulating text block)."""
    img = np.ones((200, 200, 3), dtype=np.uint8) * 255
    cv2.rectangle(img, (50, 80), (150, 120), (0, 0, 0), -1)
    return img


def test_deskew():
    img = create_synthetic_image()

    # Rotate by 15 degrees
    M = cv2.getRotationMatrix2D((100, 100), 15, 1.0)
    tilted = cv2.warpAffine(img, M, (200, 200), borderValue=(255, 255, 255))

    # Deskew
    straightened = deskew(tilted)

    # The straightened image should match the original closely
    gray = cv2.cvtColor(straightened, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY_INV)
    points = np.column_stack(np.where(thresh > 0))[:, ::-1].astype(np.float32)
    angle = cv2.minAreaRect(points)[-1]
    normalized = angle + 90 if angle <= -45 else angle - 90 if angle > 45 else angle
    assert abs(normalized) < 1.0, f"Deskew left {normalized:.2f} degrees of skew"


def test_binarize():
    # Create a grayscale image with varied lighting
    img = np.zeros((100, 100), dtype=np.uint8)
    img[0:50, :] = 100  # Dark gray
    img[50:100, :] = 200  # Light gray

    # Add some "text" strokes (black lines 2px thick)
    cv2.line(img, (20, 25), (80, 25), 0, 2)
    cv2.line(img, (20, 75), (80, 75), 0, 2)

    binary = binarize(img)

    # Binarize should output strictly 0 or 255
    unique_vals = np.unique(binary)
    assert set(unique_vals).issubset({0, 255})

    # Text regions should be 0 (black), background should be 255 (white)
    assert binary[25, 50] == 0
    assert binary[75, 50] == 0

    assert binary[10, 50] == 255
    assert binary[60, 50] == 255


def test_denoise_and_contrast():
    img = create_synthetic_image()

    # Add Gaussian noise
    noise = np.random.normal(0, 25, img.shape)
    noisy = np.clip(img.astype(np.float32) + noise, 0, 255).astype(np.uint8)

    denoised = denoise(noisy)
    enhanced = apply_clahe(denoised)

    # Output should maintain correct shape and type
    assert denoised.shape == noisy.shape
    # apply_clahe converts to grayscale — output is 2D (H, W)
    assert enhanced.shape == denoised.shape[:2]
    assert enhanced.dtype == np.uint8
    noisy_gray = cv2.cvtColor(noisy, cv2.COLOR_BGR2GRAY)
    denoised_gray = cv2.cvtColor(denoised, cv2.COLOR_BGR2GRAY)
    # A blank background region should become more uniform while the text remains dark.
    assert np.std(denoised_gray[:50, :]) < np.std(noisy_gray[:50, :])
    assert np.mean(denoised_gray[85:115, 60:140]) < 40


def test_full_pipeline():
    img = create_synthetic_image()

    # Run the orchestrator with all steps enabled
    result = preprocess_image(
        img, do_deskew=True, do_denoise=True, do_binarize=True, do_clahe=True
    )

    # Final output should be a 2D binary image
    assert len(result.shape) == 2
    assert result.dtype == np.uint8

    # Should only contain black (0) and white (255) pixels
    unique_vals = np.unique(result)
    assert set(unique_vals).issubset({0, 255})


def test_pipeline_steps_can_be_disabled():
    img = create_synthetic_image()
    result = preprocess_image(
        img,
        do_deskew=False,
        do_denoise=False,
        do_binarize=False,
        do_clahe=False,
    )
    assert np.array_equal(result, img)
    assert result is not img


def test_binarize_rejects_invalid_block_size():
    with pytest.raises(ValueError, match="odd integer"):
        binarize(np.ones((20, 20), dtype=np.uint8), block_size=10)


def test_pipeline_completes_under_one_second_on_sample_page():
    page = np.ones((800, 600, 3), dtype=np.uint8) * 255
    for y in range(60, 760, 50):
        cv2.putText(page, "ExamLens question text", (30, y), 0, 0.7, (0, 0, 0), 2)
    started = time.perf_counter()
    result = preprocess_image(page)
    assert time.perf_counter() - started < 1.0
    assert result.shape == page.shape[:2]
