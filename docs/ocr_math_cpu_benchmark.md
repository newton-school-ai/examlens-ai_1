# TrOCR and pix2tex CPU acceptance benchmark

This benchmark exercises the downloaded TrOCR and pix2tex checkpoints without
mocks. It generates a three-line clean-handwriting image with Pillow, runs the
complete line-segmentation and TrOCR page pipeline twice, and runs pix2tex twice
on a generated equation crop. It also runs equation detection, pix2tex, text
OCR, and positional reinsertion on a generated mixed page. The first
measurement includes model initialization; the acceptance timings are warm
inference after models are cached in the process.

The merge gate deliberately has more headroom than the issue minimums:

| Check | Issue requirement | Merge gate |
| --- | ---: | ---: |
| Clean-handwriting character accuracy | >80% | >85%, case-sensitive |
| Warm handwriting page time on CPU | <15 s | <12 s |
| Warm equation time on CPU | <5 s | <4 s |
| Equation correctness | Valid LaTeX | Valid and exact after presentation-only normalization |
| Positional integration | Correct position | Exact integrated text and exactly one detected equation |

The case-sensitive character error convention follows the TrOCR IAM evaluation
protocol. TrOCR reports IAM results on the Aachen line split; this repository's
timing and acceptance result remains a full-page pipeline measurement, so its
number is not presented as directly comparable to the paper's line-only CER.
The pix2tex project reports BLEU, normalized edit distance, and token accuracy
on im2latex-style data. For this small regression fixture, exact normalized
equality is a stronger and easier-to-audit correctness gate: a sign or exponent
change fails even when the output is syntactically valid LaTeX.

References: [TrOCR paper](https://arxiv.org/abs/2109.10282),
[official TrOCR implementation](https://github.com/microsoft/unilm/tree/master/trocr),
[pix2tex](https://github.com/lukas-blecher/LaTeX-OCR), and
[im2latex-100k](https://doi.org/10.5281/zenodo.56198).

Run it from the repository root:

```bash
TROCR_MODEL=microsoft/trocr-small-handwritten \
python -m scripts.benchmark_ocr_math --assert-targets
```

The optional pytest wrapper runs the same unmocked benchmark:

```bash
RUN_REAL_MODEL_TESTS=1 \
TROCR_MODEL=microsoft/trocr-small-handwritten \
pytest tests/test_real_model_cpu.py -v
```

A real page and UTF-8 ground-truth transcription can replace the generated
handwriting fixture without changing the math fixture:

```bash
TROCR_MODEL=microsoft/trocr-small-handwritten \
python -m scripts.benchmark_ocr_math \
  --handwriting-image data/handwritten_clean_writer_a.jpg \
  --handwriting-transcript data/handwritten_clean_writer_a.txt \
  --assert-targets
```

## Measured output

Run on 5 August 2026 on an Apple Silicon Mac with GPU execution disabled:

```json
{
  "environment": {
    "platform": "macOS-26.5.2-arm64-arm-64bit",
    "python": "3.11.13",
    "torch": "2.13.0",
    "device": "cpu"
  },
  "trocr": {
    "model": "microsoft/trocr-small-handwritten",
    "fixture_kind": "synthetic",
    "first_run_seconds_including_model_load": 3.497,
    "warm_page_seconds": 0.205,
    "character_accuracy": 0.9885,
    "expected": "The quick brown fox jumps\nExam answers need clear writing\nStudents solve every question",
    "actual": "The quick brown fox jumps\nExam answers need clear writing\nstudents solve every question",
    "lines_detected": 3,
    "model_device": "cpu"
  },
  "pix2tex": {
    "first_run_seconds_including_model_load": 0.786,
    "warm_equation_seconds": 0.070,
    "expected_latex": "x=2",
    "latex": "\\scriptstyle x\\;=\\;2",
    "canonical_latex": "x=2",
    "latex_matches_expected": true,
    "latex_is_valid": true,
    "confidence": 0.9,
    "model_device": "cpu",
    "mixed_page_seconds": 0.377,
    "expected_integrated_text": "Use $x=2$ now",
    "integrated_text": "Use $\\scriptstyle x\\;=\\;2$ now",
    "canonical_integrated_text": "Use $x=2$ now",
    "integrated_text_matches_expected": true,
    "mixed_page_equations_detected": 1
  }
}
```

The generated clean-handwriting fixture achieved 98.85% case-sensitive
character accuracy and processed in 0.205 seconds per three-line page after
model initialization, passing both Issue #7's published targets and the stricter
>85% / <12-second merge gates.
pix2tex produced valid
and mathematically correct LaTeX for the generated `x = 2` fixture in 0.070
seconds on CPU, below both Issue #8's five-second target and the four-second
merge gate. The benchmark
normalizes only presentational LaTeX commands before requiring exact equality
with `x=2`. The unmocked mixed-page check also detected exactly one equation and
returned `Use $x=2$ now`, proving that LaTeX is restored at the correct inline
position. The command exits non-zero if either correctness check changes.

## Supplied clean-cursive sample

The same command was run against a 778 x 940 ruled-paper page containing 11
lines of connected cursive handwriting and its manual transcription:

```json
{
  "fixture_kind": "supplied",
  "first_run_seconds_including_model_load": 3.869,
  "warm_page_seconds": 0.780,
  "character_accuracy": 0.9213,
  "lines_detected": 11,
  "model_device": "cpu"
}
```

This real sample also passes both Issue #7 targets and the stricter merge gates.
Long notebook-grid rules are
removed before projection-based line splitting, and each line is binarized and
tightly cropped before TrOCR inference.

These figures cover one deterministic synthetic fixture and one real cursive
page; they are not a broad multi-writer handwriting benchmark. Model download
and one-time initialization are reported separately by the command and are
intentionally excluded from per-page throughput.
