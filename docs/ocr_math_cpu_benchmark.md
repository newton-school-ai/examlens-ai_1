# TrOCR and pix2tex CPU acceptance benchmark

This benchmark exercises the downloaded TrOCR and pix2tex checkpoints without
mocks. It generates a three-line clean-handwriting image with Pillow, runs the
complete line-segmentation and TrOCR page pipeline twice, and runs pix2tex twice
on a generated equation crop. The first measurement includes model
initialization; the acceptance timings are warm inference after models are
cached in the process.

Run it from the repository root:

```bash
python -m scripts.benchmark_ocr_math --assert-targets
```

The optional pytest wrapper runs the same unmocked benchmark:

```bash
RUN_REAL_MODEL_TESTS=1 pytest tests/test_real_model_cpu.py -v
```

## Measured output

Run on 27 July 2026 on an Apple Silicon Mac with GPU execution disabled:

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
    "first_run_seconds_including_model_load": 8.57,
    "warm_page_seconds": 0.225,
    "character_accuracy": 0.977,
    "expected": "The quick brown fox jumps\nExam answers need clear writing\nStudents solve every question",
    "actual": "The quick brown fox jumps .\nExam answers need clear writing\nstudents solve every question",
    "lines_detected": 3,
    "model_device": "cpu"
  },
  "pix2tex": {
    "first_run_seconds_including_model_load": 1.36,
    "warm_equation_seconds": 0.165,
    "latex": "\\mathbf{x}^{-2}+\\mathbf{y}^{-2}=\\mathbf{r}^{-2}",
    "confidence": 0.9,
    "model_device": "cpu"
  }
}
```

The generated clean-handwriting fixture achieved 97.7% character accuracy and
processed in 0.225 seconds per three-line page after model initialization,
passing Issue #7's >80% and <15 seconds/page CPU targets. pix2tex produced valid
LaTeX in 0.165 seconds on CPU, below Issue #8's five-second equation target.

These figures are for a deterministic synthetic smoke fixture, not a broad
handwriting benchmark. Model download and one-time initialization are reported
separately by the command and are intentionally excluded from per-page
throughput.
