"""Detect mathematical regions and convert them to KaTeX-compatible LaTeX."""

from __future__ import annotations

import argparse
import os
import re
from typing import Any, Sequence

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

_latex_model: Any | None = None

MATH_TOKEN = re.compile(
    r"(?:^(?:[=+*/^<>≤≥±×÷])$"
    r"|[∫∑√∞πθαβγδ∆λμσΣΩ]"
    r"|\b(?:sin|cos|tan|log|lim)\b"
    r"|\b\d+(?:\.\d+)?\s*[-/^]\s*[A-Za-z0-9]"
    r"|\b[A-Za-z]\s*[-/^]\s*\d+\b"
    r"|\b[A-Za-z0-9]\s*[=+*<>]\s*[A-Za-z0-9]\b)",
    re.IGNORECASE,
)

STANDALONE_OPERATOR = re.compile(r"^[=+*/^<>≤≥±×÷]$")
MATH_OPERAND = re.compile(r"^(?:[A-Za-z]|\d+(?:\.\d+)?|[A-Za-z]\w*[\^_]\w+|\([^)]*\))$")

KATEX_COMMANDS = {
    "Delta",
    "Gamma",
    "Lambda",
    "Omega",
    "Phi",
    "Pi",
    "Psi",
    "Sigma",
    "Theta",
    "alpha",
    "approx",
    "array",
    "bar",
    "begin",
    "beta",
    "bf",
    "binom",
    "cal",
    "cdot",
    "chi",
    "cos",
    "cot",
    "csc",
    "ddot",
    "delta",
    "det",
    "dfrac",
    "displaystyle",
    "div",
    "dot",
    "exp",
    "ell",
    "end",
    "epsilon",
    "eta",
    "exists",
    "forall",
    "frac",
    "gamma",
    "ge",
    "geq",
    "hat",
    "in",
    "infty",
    "int",
    "kappa",
    "lambda",
    "le",
    "left",
    "leq",
    "lim",
    "limits",
    "ln",
    "log",
    "longrightarrow",
    "mathbb",
    "mathbf",
    "mathcal",
    "mathit",
    "mathfrak",
    "mathrm",
    "mathsf",
    "mathtt",
    "mu",
    "max",
    "min",
    "nabla",
    "neq",
    "notin",
    "nolimits",
    "nu",
    "omega",
    "operatorname",
    "overline",
    "overbrace",
    "overset",
    "partial",
    "phi",
    "pi",
    "pm",
    "prod",
    "psi",
    "rho",
    "right",
    "sec",
    "scriptstyle",
    "scriptscriptstyle",
    "sigma",
    "sin",
    "sqrt",
    "stackrel",
    "substack",
    "sum",
    "tan",
    "tau",
    "text",
    "textstyle",
    "tfrac",
    "theta",
    "times",
    "to",
    "underline",
    "underbrace",
    "underset",
    "upsilon",
    "varepsilon",
    "varphi",
    "varpi",
    "varrho",
    "varsigma",
    "vartheta",
    "vec",
    "xi",
    "zeta",
}

KATEX_ENVIRONMENTS = {
    "aligned",
    "array",
    "bmatrix",
    "cases",
    "gathered",
    "matrix",
    "pmatrix",
    "smallmatrix",
    "Vmatrix",
    "vmatrix",
}


class EquationRegion(BaseModel):
    """A rectangular page region likely to contain an equation."""

    x: int
    y: int
    width: int
    height: int
    detection_confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    inline: bool = False


class EquationResult(EquationRegion):
    """Recognized equation and confidence."""

    latex: str
    confidence: float = Field(ge=0.0, le=1.0)
    needs_correction: bool = False


class MathAwareTextResult(BaseModel):
    """OCR text with recognized equations embedded in page reading order."""

    text: str
    equations: list[EquationResult]
    text_confidence: float = Field(ge=0.0, le=1.0)


def get_latex_model() -> Any:
    """Return a cached pix2tex recognizer, loading its weights only once."""
    global _latex_model
    if _latex_model is None:
        try:
            from pix2tex.cli import LatexOCR
        except ImportError as exc:  # pragma: no cover - depends on local extras
            raise RuntimeError(
                "Equation recognition requires pix2tex. Install project "
                "dependencies with `pip install -r requirements.txt`."
            ) from exc
        _latex_model = LatexOCR()
        # pix2tex defaults to temperature-based multinomial sampling. OCR must
        # be reproducible, so use a near-greedy temperature that makes repeated
        # inference on the same crop stable while preserving the upstream API.
        _latex_model.args.temperature = 0.01
    return _latex_model


def _mask(image: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 else image
    return cv2.threshold(
        cv2.GaussianBlur(gray, (3, 3), 0),
        0,
        255,
        cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU,
    )[1]


def _line_regions(mask: np.ndarray) -> list[tuple[int, int, int, int]]:
    joined = cv2.dilate(
        mask,
        cv2.getStructuringElement(cv2.MORPH_RECT, (max(10, mask.shape[1] // 100), 3)),
    )
    contours, _ = cv2.findContours(joined, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    boxes = [
        cv2.boundingRect(contour)
        for contour in contours
        if cv2.contourArea(contour) >= max(8, mask.size // 1_000_000)
    ]
    return sorted(boxes, key=lambda box: (box[1], box[0]))


def _ocr_math_regions(image: np.ndarray) -> list[EquationRegion]:
    """Find inline/display candidates from Tesseract's word layout."""
    if pytesseract is None:
        return []
    try:
        data = pytesseract.image_to_data(
            image, lang="eng", config="--oem 1 --psm 6", output_type=Output.DICT
        )
    except (TesseractError, TesseractNotFoundError):
        return []

    by_line: dict[tuple[int, int, int], list[int]] = {}
    for index, raw_text in enumerate(data["text"]):
        text = raw_text.strip()
        if not text:
            continue
        key = (
            int(data.get("block_num", [0] * len(data["text"]))[index]),
            int(data.get("par_num", [0] * len(data["text"]))[index]),
            int(data.get("line_num", [index] * len(data["text"]))[index]),
        )
        by_line.setdefault(key, []).append(index)

    page_height, page_width = image.shape[:2]
    regions: list[EquationRegion] = []
    for indices in by_line.values():
        math_indices = []
        for position, index in enumerate(indices):
            text = data["text"][index].strip()
            if not MATH_TOKEN.search(text) or float(data["conf"][index]) <= 0:
                continue
            if STANDALONE_OPERATOR.fullmatch(text):
                if position == 0 or position == len(indices) - 1:
                    continue
                previous_text = data["text"][indices[position - 1]].strip()
                next_text = data["text"][indices[position + 1]].strip()
                if not (
                    MATH_OPERAND.fullmatch(previous_text)
                    and MATH_OPERAND.fullmatch(next_text)
                ):
                    continue
            math_indices.append(index)
        if not math_indices:
            continue
        # Include one neighbouring token so "x = 2" is not cropped to "=".
        first = max(indices.index(math_indices[0]) - 1, 0)
        last = min(indices.index(math_indices[-1]) + 1, len(indices) - 1)
        selected = indices[first : last + 1]
        left = min(int(data["left"][index]) for index in selected)
        top = min(int(data["top"][index]) for index in selected)
        right = max(
            int(data["left"][index]) + int(data["width"][index]) for index in selected
        )
        bottom = max(
            int(data["top"][index]) + int(data["height"][index]) for index in selected
        )
        region_width = right - left
        region_height = bottom - top
        if (
            region_height > page_height * 0.35
            or region_width * region_height > page_width * page_height * 0.20
        ):
            continue
        mean_confidence = np.mean(
            [max(0.0, float(data["conf"][index])) for index in math_indices]
        )
        regions.append(
            EquationRegion(
                x=left,
                y=top,
                width=region_width,
                height=region_height,
                detection_confidence=min(0.98, 0.65 + mean_confidence / 300),
                inline=len(math_indices) < len(indices),
            )
        )
    return regions


def _visual_math_score(mask: np.ndarray, box: tuple[int, int, int, int]) -> float:
    """Score fractions, stacked scripts, integrals, and matrix-like layouts."""
    x, y, width, height = box
    crop = mask[y : y + height, x : x + width]
    if crop.size == 0:
        return 0.0
    count, _, stats, _ = cv2.connectedComponentsWithStats(crop, 8)
    components = [
        stats[index] for index in range(1, count) if stats[index, cv2.CC_STAT_AREA] >= 2
    ]
    if not components:
        return 0.0
    heights = np.array([item[cv2.CC_STAT_HEIGHT] for item in components], dtype=float)
    tops = np.array([item[cv2.CC_STAT_TOP] for item in components], dtype=float)
    spread = min(1.0, float(np.std(tops) / (np.mean(heights) + 1e-6)))
    varied_size = min(1.0, float(np.std(heights) / (np.mean(heights) + 1e-6)))
    long_bars = sum(
        item[cv2.CC_STAT_WIDTH] >= width * 0.15
        and item[cv2.CC_STAT_HEIGHT] <= max(3, height * 0.12)
        for item in components
    )
    fraction_score = min(1.0, long_bars / 2)
    tall_symbols = sum(item[cv2.CC_STAT_HEIGHT] >= height * 0.7 for item in components)
    tall_score = min(1.0, tall_symbols / 2)
    return (
        0.32 * spread + 0.24 * varied_size + 0.28 * fraction_score + 0.16 * tall_score
    )


def _structural_math_regions(mask: np.ndarray) -> list[EquationRegion]:
    """Group stacked fractions and bracketed matrices before line detection."""
    count, _, stats, _ = cv2.connectedComponentsWithStats(mask, 8)
    minimum_component_area = max(4, mask.size // 500_000)
    components = [
        stats[index]
        for index in range(1, count)
        if stats[index, cv2.CC_STAT_AREA] >= minimum_component_area
        and stats[index, cv2.CC_STAT_HEIGHT] >= 3
    ]
    if not components:
        return []
    typical_height = float(np.median([item[cv2.CC_STAT_HEIGHT] for item in components]))
    page_height, page_width = mask.shape
    regions: list[EquationRegion] = []

    # A fraction bar has ink both above and below it in the same horizontal span.
    horizontal = cv2.morphologyEx(
        mask,
        cv2.MORPH_OPEN,
        cv2.getStructuringElement(cv2.MORPH_RECT, (max(12, page_width // 120), 1)),
    )
    contours, _ = cv2.findContours(
        horizontal, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )
    for contour in contours:
        x, y, width, height = cv2.boundingRect(contour)
        if (
            width < max(20, typical_height * 5)
            or width > page_width * 0.75
            or height > max(4, typical_height * 0.35)
        ):
            continue
        vertical_reach = round(max(20, typical_height * 3))
        side_padding = round(max(8, typical_height))
        left = max(0, x - side_padding)
        right = min(page_width, x + width + side_padding)
        top = max(0, y - vertical_reach)
        bottom = min(page_height, y + height + vertical_reach)
        above_window = mask[top:y, x : x + width]
        below_window = mask[y + height : bottom, x : x + width]
        above_ink = np.count_nonzero(above_window)
        below_ink = np.count_nonzero(below_window)
        minimum_neighbour_ink = max(8, round(width * 0.12))
        if above_ink < minimum_neighbour_ink or below_ink < minimum_neighbour_ink:
            continue
        above_columns = np.flatnonzero(np.any(above_window > 0, axis=0))
        below_columns = np.flatnonzero(np.any(below_window > 0, axis=0))
        if above_columns.size == 0 or below_columns.size == 0:
            continue
        overlap_width = max(
            0,
            min(int(above_columns.max()), int(below_columns.max()))
            - max(int(above_columns.min()), int(below_columns.min())),
        )
        smaller_span = min(
            int(above_columns.max() - above_columns.min() + 1),
            int(below_columns.max() - below_columns.min() + 1),
        )
        if overlap_width / max(1, smaller_span) < 0.30:
            continue
        points_y, points_x = np.where(mask[top:bottom, left:right] > 0)
        region_left = left + int(points_x.min())
        region_top = top + int(points_y.min())
        region_right = left + int(points_x.max()) + 1
        region_bottom = top + int(points_y.max()) + 1
        region_width = region_right - region_left
        region_height = region_bottom - region_top
        if region_width > typical_height * 12 or region_height > typical_height * 7:
            continue
        regions.append(
            EquationRegion(
                x=region_left,
                y=region_top,
                width=region_width,
                height=region_height,
                detection_confidence=0.82,
                inline=False,
            )
        )

    # Matrices have a pair of similarly tall, narrow brackets surrounding
    # multi-row content. Requiring the pair avoids treating ordinary ascenders,
    # page borders, or table rules as equations.
    tall_components = []
    for component in components:
        width = int(component[cv2.CC_STAT_WIDTH])
        height = int(component[cv2.CC_STAT_HEIGHT])
        if height >= typical_height * 3 and width <= max(10, height * 0.35):
            tall_components.append(component)

    for index, first in enumerate(tall_components):
        first_y = int(first[cv2.CC_STAT_TOP])
        first_width = int(first[cv2.CC_STAT_WIDTH])
        first_height = int(first[cv2.CC_STAT_HEIGHT])
        for second in tall_components[index + 1 :]:
            second_y = int(second[cv2.CC_STAT_TOP])
            second_width = int(second[cv2.CC_STAT_WIDTH])
            second_height = int(second[cv2.CC_STAT_HEIGHT])
            vertical_overlap = max(
                0,
                min(first_y + first_height, second_y + second_height)
                - max(first_y, second_y),
            )
            if vertical_overlap / min(first_height, second_height) < 0.75:
                continue
            if (
                max(first_height, second_height) / min(first_height, second_height)
                > 1.4
            ):
                continue

            left_component, right_component = sorted(
                (first, second), key=lambda item: item[cv2.CC_STAT_LEFT]
            )
            left = int(left_component[cv2.CC_STAT_LEFT])
            right = int(
                right_component[cv2.CC_STAT_LEFT] + right_component[cv2.CC_STAT_WIDTH]
            )
            if not typical_height * 2 <= right - left <= page_width * 0.65:
                continue
            top = max(0, min(first_y, second_y) - 3)
            bottom = min(
                page_height,
                max(first_y + first_height, second_y + second_height) + 3,
            )
            local = mask[top:bottom, left:right]
            local_count, _, local_stats, _ = cv2.connectedComponentsWithStats(local, 8)
            inner_components = [
                item
                for item in local_stats[1:local_count]
                if item[cv2.CC_STAT_AREA] >= minimum_component_area
                and item[cv2.CC_STAT_LEFT] > first_width
                and item[cv2.CC_STAT_LEFT] + item[cv2.CC_STAT_WIDTH]
                < local.shape[1] - second_width
            ]
            if len(inner_components) < 4:
                continue
            inner_centres = [
                item[cv2.CC_STAT_TOP] + item[cv2.CC_STAT_HEIGHT] / 2
                for item in inner_components
            ]
            if max(inner_centres) - min(inner_centres) < typical_height:
                continue
            regions.append(
                EquationRegion(
                    x=left,
                    y=top,
                    width=right - left,
                    height=bottom - top,
                    detection_confidence=0.78,
                    inline=False,
                )
            )
            break
    return regions


def _overlap(first: EquationRegion, second: EquationRegion) -> float:
    left, top = max(first.x, second.x), max(first.y, second.y)
    right = min(first.x + first.width, second.x + second.width)
    bottom = min(first.y + first.height, second.y + second.height)
    intersection = max(0, right - left) * max(0, bottom - top)
    smaller = min(first.width * first.height, second.width * second.height)
    return intersection / smaller if smaller else 0.0


def _merge_regions(regions: list[EquationRegion]) -> list[EquationRegion]:
    merged: list[EquationRegion] = []
    for region in sorted(regions, key=lambda item: (item.y, item.x)):
        duplicate = next(
            (item for item in merged if _overlap(item, region) > 0.55), None
        )
        if duplicate is None:
            merged.append(region)
            continue
        left, top = min(duplicate.x, region.x), min(duplicate.y, region.y)
        right = max(duplicate.x + duplicate.width, region.x + region.width)
        bottom = max(duplicate.y + duplicate.height, region.y + region.height)
        duplicate.x, duplicate.y = left, top
        duplicate.width, duplicate.height = right - left, bottom - top
        duplicate.detection_confidence = max(
            duplicate.detection_confidence, region.detection_confidence
        )
        duplicate.inline = duplicate.inline or region.inline
    return merged


def detect_equation_regions(
    image: np.ndarray, min_confidence: float = 0.45
) -> list[EquationRegion]:
    """Detect display and inline equation regions in a mixed-content page."""
    if image is None or image.size == 0:
        raise ValueError("A non-empty image is required for equation detection")
    if not 0 <= min_confidence <= 1:
        raise ValueError("min_confidence must be between 0 and 1")

    mask = _mask(image)
    candidates = _ocr_math_regions(image) + _structural_math_regions(mask)
    for box in _line_regions(mask):
        score = _visual_math_score(mask, box)
        if score >= max(min_confidence, 0.82):
            x, y, width, height = box
            candidates.append(
                EquationRegion(
                    x=x,
                    y=y,
                    width=width,
                    height=height,
                    detection_confidence=min(0.95, score),
                    inline=False,
                )
            )
    page_height, page_width = image.shape[:2]
    return [
        region
        for region in _merge_regions(candidates)
        if region.detection_confidence >= min_confidence
        and region.width * region.height <= page_width * page_height * 0.50
        and not (
            region.width >= page_width * 0.90 and region.height >= page_height * 0.20
        )
    ]


def normalize_latex(latex: str) -> str:
    """Strip display delimiters and normalize common pix2tex wrappers."""
    latex = latex.strip()
    wrappers = (("$$", "$$"), ("\\[", "\\]"), ("\\(", "\\)"), ("$", "$"))
    for opening, closing in wrappers:
        if latex.startswith(opening) and latex.endswith(closing):
            latex = latex[len(opening) : -len(closing)].strip()
            break
    latex = re.sub(r"\s+", " ", latex)
    return latex.replace(r"\displaystyle ", "").strip()


def is_valid_latex(latex: str) -> bool:
    """Perform a conservative structural and KaTeX-command compatibility check."""
    if not latex or "\x00" in latex:
        return False
    depth = 0
    unescaped_dollars = 0
    for index, char in enumerate(latex):
        backslashes = 0
        cursor = index - 1
        while cursor >= 0 and latex[cursor] == "\\":
            backslashes += 1
            cursor -= 1
        escaped = backslashes % 2 == 1
        if char == "{" and not escaped:
            depth += 1
        elif char == "}" and not escaped:
            depth -= 1
            if depth < 0:
                return False
        elif char == "$" and not escaped:
            unescaped_dollars += 1
    if depth != 0 or unescaped_dollars:
        return False

    environment_stack: list[str] = []
    for match in re.finditer(r"\\(begin|end)\{([A-Za-z*]+)\}", latex):
        action, environment = match.groups()
        if environment not in KATEX_ENVIRONMENTS:
            return False
        if action == "begin":
            environment_stack.append(environment)
        elif not environment_stack or environment_stack.pop() != environment:
            return False
    if environment_stack:
        return False

    commands = set(re.findall(r"\\([A-Za-z]+)", latex))
    if not commands.issubset(KATEX_COMMANDS):
        return False
    delimiter_depth = 0
    for match in re.finditer(r"\\(left|right)\b", latex):
        if match.group(1) == "left":
            delimiter_depth += 1
        elif delimiter_depth == 0:
            return False
        else:
            delimiter_depth -= 1
    if delimiter_depth:
        return False
    return True


def _latex_quality(latex: str) -> float:
    if not latex:
        return 0.0
    score = 0.62
    if is_valid_latex(latex):
        score += 0.18
    if re.search(r"[=+\-^_]|\\(?:frac|int|sum|sqrt|begin)", latex):
        score += 0.10
    if "\ufffd" in latex or len(latex) > 1000:
        score -= 0.25
    return max(0.0, min(0.95, score))


def recognize_equation(image: np.ndarray) -> tuple[str, float]:
    """Recognize one equation crop, accepting pix2tex API output variants."""
    if image.ndim == 2:
        rgb = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
    else:
        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    output = get_latex_model()(Image.fromarray(rgb))
    confidence: float | None = None
    if isinstance(output, dict):
        latex = str(output.get("latex", output.get("text", "")))
        raw_confidence = output.get("confidence", output.get("score"))
        confidence = float(raw_confidence) if raw_confidence is not None else None
    elif isinstance(output, (tuple, list)):
        latex = str(output[0]) if output else ""
        confidence = float(output[1]) if len(output) > 1 else None
    else:
        latex = str(output)
    latex = normalize_latex(latex)
    if confidence is None:
        confidence = _latex_quality(latex)
    return latex, max(0.0, min(1.0, confidence))


def extract_equations(
    image_path: str,
    detection_threshold: float = 0.45,
    confidence_threshold: float = 0.65,
) -> list[EquationResult]:
    """Detect and recognize every equation on a page in reading order."""
    image = cv2.imread(os.fspath(image_path))
    if image is None:
        raise ValueError(f"Could not read image from {image_path}")
    if not 0 <= confidence_threshold <= 1:
        raise ValueError("confidence_threshold must be between 0 and 1")

    page_height, page_width = image.shape[:2]
    results: list[EquationResult] = []
    for region in detect_equation_regions(image, detection_threshold):
        pad = max(3, region.height // 8)
        left, top = max(0, region.x - pad), max(0, region.y - pad)
        right = min(page_width, region.x + region.width + pad)
        bottom = min(page_height, region.y + region.height + pad)
        latex, recognition_confidence = recognize_equation(
            image[top:bottom, left:right]
        )
        confidence = (recognition_confidence * region.detection_confidence) ** 0.5
        results.append(
            EquationResult(
                **region.model_dump(),
                latex=latex,
                confidence=max(0.0, min(1.0, confidence)),
                needs_correction=(
                    confidence < confidence_threshold or not is_valid_latex(latex)
                ),
            )
        )
    return results


def _vertical_overlap(first: Any, second: Any) -> float:
    """Return vertical overlap relative to the shorter item."""
    top = max(first.y, second.y)
    bottom = min(first.y + first.height, second.y + second.height)
    shorter = min(first.height, second.height)
    return max(0, bottom - top) / shorter if shorter else 0.0


def _nearest_word_boundary(text: str, target: int) -> int:
    """Choose the closest whitespace boundary to a character offset."""
    boundaries = [0, len(text)]
    boundaries.extend(match.end() for match in re.finditer(r"\s+", text))
    return min(boundaries, key=lambda boundary: abs(boundary - target))


def merge_equations_into_text(
    text_lines: Sequence[Any], equations: Sequence[EquationResult]
) -> str:
    """Merge positioned OCR lines and equations into one Markdown/LaTeX string.

    Text lines must expose ``text``, ``x``, ``y``, ``width``, and ``height``.
    Inline equations are inserted at the nearest word boundary inferred from
    their horizontal page coordinate. Display equations remain separate lines.
    """
    ordered_lines = sorted(text_lines, key=lambda item: (item.y, item.x))
    inline_by_line: dict[int, list[EquationResult]] = {}
    display_equations: list[EquationResult] = []

    for equation in equations:
        candidates = [
            (index, _vertical_overlap(line, equation))
            for index, line in enumerate(ordered_lines)
        ]
        best_index, best_overlap = max(
            candidates, key=lambda item: item[1], default=(-1, 0)
        )
        if equation.inline and best_overlap >= 0.35:
            inline_by_line.setdefault(best_index, []).append(equation)
        else:
            display_equations.append(equation)

    blocks: list[tuple[int, int, str]] = []
    for index, line in enumerate(ordered_lines):
        text = line.text
        insertions: list[tuple[int, str]] = []
        for equation in inline_by_line.get(index, []):
            relative_center = (equation.x + equation.width / 2 - line.x) / max(
                1, line.width
            )
            target = round(max(0.0, min(1.0, relative_center)) * len(text))
            offset = _nearest_word_boundary(text, target)
            insertions.append((offset, f"${equation.latex}$"))
        for offset, token in sorted(insertions, reverse=True):
            separator_before = "" if offset == 0 or text[offset - 1].isspace() else " "
            separator_after = (
                "" if offset == len(text) or text[offset].isspace() else " "
            )
            text = (
                text[:offset]
                + separator_before
                + token
                + separator_after
                + text[offset:]
            )
        blocks.append((line.y, line.x, text.strip()))

    blocks.extend(
        (equation.y, equation.x, f"$${equation.latex}$$")
        for equation in display_equations
    )
    return "\n".join(
        text
        for _, _, text in sorted(blocks, key=lambda item: (item[0], item[1]))
        if text
    )


def extract_text_with_equations(
    image_path: str,
    detection_threshold: float = 0.45,
    equation_confidence_threshold: float = 0.65,
    text_confidence_threshold: float | None = None,
    detect_mixed: bool = True,
) -> MathAwareTextResult:
    """Extract page text and put LaTeX back at its spatial reading position."""
    from src.cv.ocr_handwritten import extract_text_handwritten_image

    image = cv2.imread(os.fspath(image_path))
    if image is None:
        raise ValueError(f"Could not read image from {image_path}")
    equations = extract_equations(
        image_path,
        detection_threshold=detection_threshold,
        confidence_threshold=equation_confidence_threshold,
    )

    # OCR the non-math pixels only. This prevents the recognizer's garbled
    # rendering of an equation from being duplicated beside its LaTeX token.
    text_only_image = image.copy()
    page_height, page_width = text_only_image.shape[:2]
    for equation in equations:
        pad_x = max(4, equation.height // 4)
        pad_y = max(2, equation.height // 12)
        left = max(0, equation.x - pad_x)
        top = max(0, equation.y - pad_y)
        right = min(page_width, equation.x + equation.width + pad_x)
        bottom = min(page_height, equation.y + equation.height + pad_y)
        text_only_image[top:bottom, left:right] = 255

    text_result = extract_text_handwritten_image(
        text_only_image,
        confidence_threshold=text_confidence_threshold,
        detect_mixed=detect_mixed,
        deskew_page=False,
    )
    return MathAwareTextResult(
        text=merge_equations_into_text(text_result.lines, equations),
        equations=equations,
        text_confidence=text_result.confidence,
    )


def _main() -> int:
    parser = argparse.ArgumentParser(
        description="Detect page equations and convert them to LaTeX"
    )
    parser.add_argument("--input", required=True, help="Path to an input page image")
    parser.add_argument(
        "--with-text",
        action="store_true",
        help="OCR the page and embed equations into the extracted text",
    )
    args = parser.parse_args()
    try:
        if args.with_text:
            page = extract_text_with_equations(args.input)
            results = page.equations
        else:
            page = None
            results = extract_equations(args.input)
    except (ValueError, RuntimeError) as exc:
        parser.error(str(exc))
    print(f"Equations detected: {len(results)}")
    for equation in results:
        flag = " [CHECK]" if equation.needs_correction else ""
        print(
            f"[{equation.confidence:.2f}] "
            f"({equation.x}, {equation.y}, {equation.width}, {equation.height}): "
            f"{equation.latex}{flag}"
        )
    if page is not None:
        print("\nIntegrated text:")
        print(page.text)
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
