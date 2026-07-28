"""Opt-in unmocked CPU acceptance test for the OCR and math checkpoints."""

import os

import pytest

from scripts.benchmark_ocr_math import run_benchmark

pytestmark = [
    pytest.mark.real_models,
    pytest.mark.skipif(
        os.getenv("RUN_REAL_MODEL_TESTS") != "1",
        reason="set RUN_REAL_MODEL_TESTS=1 to run downloaded CPU checkpoints",
    ),
]


def test_trocr_and_pix2tex_run_on_cpu_and_meet_acceptance_targets():
    result = run_benchmark()
    trocr = result["trocr"]
    pix2tex = result["pix2tex"]

    assert result["environment"]["device"] == "cpu"
    assert trocr["model_device"] == "cpu"
    assert trocr["character_accuracy"] > 0.8
    assert trocr["warm_page_seconds"] < 15
    assert pix2tex["model_device"] == "cpu"
    assert pix2tex["warm_equation_seconds"] < 5
    assert pix2tex["latex"]
