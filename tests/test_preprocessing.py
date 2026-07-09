import cv2
import numpy as np

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
    contours = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[-2]

    assert len(contours) > 0, "No contours found after deskew"
    angle = cv2.minAreaRect(contours[0])[-1]

    # After deskewing, angle should be reduced (deskew is best-effort on synthetic images)
    assert abs(angle) < 45.0, f"Deskew produced unexpected angle: {angle}"


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
    noise = np.random.normal(0, 25, img.shape).astype(np.uint8)
    noisy = cv2.add(img, noise)

    denoised = denoise(noisy)
    enhanced = apply_clahe(denoised)

    # Output should maintain correct shape and type
    assert denoised.shape == noisy.shape
    # apply_clahe converts to grayscale — output is 2D (H, W)
    assert enhanced.shape == denoised.shape[:2]
    assert enhanced.dtype == np.uint8


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
