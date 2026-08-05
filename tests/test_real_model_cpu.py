"""Opt-in unmocked CPU acceptance test for the OCR and math checkpoints."""

import os

import pytest

from scripts.benchmark_ocr_math import (
    EXPECTED_EQUATION_LATEX,
    EXPECTED_INTEGRATED_TEXT,
    MAX_EQUATION_SECONDS,
    MAX_HANDWRITING_PAGE_SECONDS,
    MIN_HANDWRITING_CHARACTER_ACCURACY,
    _character_accuracy,
    normalize_benchmark_latex,
    normalize_integrated_math_text,
    run_benchmark,
)


@pytest.mark.real_models
@pytest.mark.skipif(
    os.getenv("RUN_REAL_MODEL_TESTS") != "1",
    reason="set RUN_REAL_MODEL_TESTS=1 to run downloaded CPU checkpoints",
)
def test_trocr_and_pix2tex_run_on_cpu_and_meet_acceptance_targets():
    result = run_benchmark(
        handwriting_image=os.getenv("REAL_HANDWRITING_IMAGE"),
        handwriting_transcript=os.getenv("REAL_HANDWRITING_TRANSCRIPT"),
    )
    trocr = result["trocr"]
    pix2tex = result["pix2tex"]

    assert result["environment"]["device"] == "cpu"
    assert trocr["model_device"] == "cpu"
    assert trocr["character_accuracy"] > MIN_HANDWRITING_CHARACTER_ACCURACY
    assert trocr["warm_page_seconds"] < MAX_HANDWRITING_PAGE_SECONDS
    assert pix2tex["model_device"] == "cpu"
    assert pix2tex["warm_equation_seconds"] < MAX_EQUATION_SECONDS
    assert (
        pix2tex["canonical_latex"]
        == pix2tex["expected_latex"]
        == EXPECTED_EQUATION_LATEX
    )
    assert pix2tex["latex_matches_expected"] is True
    assert pix2tex["latex_is_valid"] is True
    assert pix2tex["canonical_integrated_text"] == EXPECTED_INTEGRATED_TEXT
    assert pix2tex["integrated_text_matches_expected"] is True
    assert pix2tex["mixed_page_equations_detected"] == 1


def test_benchmark_normalization_preserves_fixture_math():
    assert normalize_benchmark_latex(r"\scriptstyle x=2") == EXPECTED_EQUATION_LATEX
    assert (
        normalize_integrated_math_text(r"Use $\scriptstyle x=2$ now")
        == EXPECTED_INTEGRATED_TEXT
    )


def test_equation_comparison_rejects_sign_changed_exponents():
    expected = "x^2+y^2=r^2"
    incorrect = r"\mathbf{x}^{-2}+\mathbf{y}^{-2}=\mathbf{r}^{-2}"

    assert normalize_benchmark_latex(expected) == expected
    assert normalize_benchmark_latex(incorrect) != normalize_benchmark_latex(expected)


def test_handwriting_accuracy_is_case_sensitive_like_iam_cer():
    assert _character_accuracy("Students", "students") == pytest.approx(7 / 8)


def test_real_handwriting_fixture_requires_image_and_transcript_together():
    with pytest.raises(ValueError, match="must be supplied together"):
        run_benchmark(handwriting_image="handwriting.png")
