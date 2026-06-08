# ExamLens AI

Agentic PYQ (Previous Year Question) analysis system that extracts questions from exam papers using OCR, generates step-by-step solutions, analyzes topic frequency, predicts important topics, and creates personalized mock exams.

Supports both university semester exams (AKTU, VTU, Anna University, etc.) and competitive exams (JEE, NEET, GATE, CAT, UPSC).

Built by a 5-student pod at Newton School of Technology.

---

## Why ExamLens? (What ChatGPT/Claude Can't Do)

ChatGPT or Claude can answer one question at a time — but they forget everything next conversation. ExamLens is a **system** that accumulates data, finds patterns, and gets smarter the more papers it processes.

**Persistent memory across papers** — ExamLens builds a searchable database across 100+ papers spanning 10+ years. Every question, topic, and year is stored and queryable.

**ML-powered pattern detection & prediction** — "Binary Trees appeared in GATE 2018-2020, skipped 2021, came back 2022-2024 with increasing marks → 92% chance of appearing in 2025." No chatbot tracks this. ExamLens uses linear regression for rising/falling trends, standard deviation analysis for stable topics, autocorrelation for cyclic patterns (topics that appear every 2-3 years), and gap analysis (absent high-frequency topics get boosted). These statistical signals feed into a multi-factor importance scorer that ranks every topic by predicted probability.

**Personalized to your weaknesses** — Claude gives the same study plan to everyone. ExamLens knows *you* scored 30% on Graph Algorithms across 3 mocks but 90% on Arrays. Your study plan adapts after every mock test.

**Realistic mock tests from real questions** — ChatGPT invents random questions. ExamLens pulls actual PYQ questions, matches the exact exam pattern (GATE: 65 questions, 100 marks, correct topic distribution), and grades you instantly.

**Automatic paper collection** — No googling for PDFs on sketchy sites. The Playwright-based scraper fetches papers directly from official exam portals, OCRs them, and makes every question searchable.

**Visual analytics** — Topic-year heatmaps, trend charts, marks distribution, and prediction rankings across 10+ years of papers. You can't get this from a chat prompt.

---

## ML/Statistical Algorithms Used

| Algorithm | Where Used | Purpose |
|-----------|-----------|---------|
| Linear Regression (slope) | Trend Detector | Classify topics as rising or falling over 3+ years |
| Standard Deviation | Trend Detector | Identify stable topics (low variance in frequency) |
| Autocorrelation | Trend Detector | Detect cyclic topics that appear every N years |
| Gap Analysis | Prediction Agent | Boost probability for topics absent despite high historical frequency |
| Multi-factor Weighted Scoring | Importance Scorer | Combine frequency + trend + recency + gap + marks weight into a single prediction score |
| YOLOv8 (Object Detection) | Layout Detector | Detect question blocks, marks indicators, headers, diagrams in paper images |
| TrOCR (Transformer OCR) | Handwritten OCR | Sequence-to-sequence model for handwritten text recognition |
| pix2tex (Vision Transformer) | Math Extractor | Convert equation images to LaTeX strings |
| Adaptive Thresholding | Preprocessing | Binarize unevenly lit document images |
| CLAHE | Preprocessing | Enhance contrast in poorly lit scans |
| Cosine Similarity + LLM | Deduplicator | Detect paraphrased duplicate questions across years |

---

## Quick Start

```bash
git clone https://github.com/newton-school-ai/examlens-ai.git
cd examlens-ai
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Add your Groq API key to .env

# Install Tesseract OCR
# macOS: brew install tesseract
# Ubuntu: sudo apt install tesseract-ocr tesseract-ocr-hin

# Start backend
uvicorn src.api.main:app --reload

# Start frontend (separate terminal)
cd frontend && npm install && npm run dev
```

---

## Tech Stack

| Layer | Tools |
|-------|-------|
| Agent Orchestration | LangGraph |
| OCR (Printed) | Tesseract 5 + EasyOCR |
| OCR (Handwritten) | TrOCR (Microsoft) |
| Math Extraction | pix2tex (image to LaTeX) |
| Layout Detection | YOLOv8 |
| Web Scraping | Playwright |
| LLM | Groq (free tier) |
| Backend | FastAPI + PostgreSQL + Alembic |
| Frontend | React + Tailwind CSS |
| Deployment | Docker + Railway/Render |

---

## Project Structure

```
src/
  agents/       Pipeline orchestrator, topic tagger, answer generator, verifier,
                prediction, mock generator, study planner, scraper
  cv/           Preprocessing, printed OCR, handwritten OCR, math extractor, layout detector
  ingestion/    PDF handler, image handler, page extractor
  parsing/      Question parser, metadata extractor, splitter, deduplicator
  analysis/     Frequency analyzer, trend detector, importance scorer
  mock/         Paper generator, grader, progress tracker
  api/          FastAPI routes (upload, questions, solutions, analytics, mock, study)
  models/       SQLAlchemy models (User, Exam, Paper, Question, Solution, Topic, MockTest)
  config/       Settings, enums
tests/
notebooks/      OCR benchmarking, layout training, answer quality evaluation
frontend/       React + Tailwind dashboards
```

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for branch strategy, PR workflow, and coding standards.
See [DEVELOPMENT_GUIDE.md](DEVELOPMENT_GUIDE.md) for full setup instructions.
See [POD_GUIDE.md](POD_GUIDE.md) for team collaboration model.

---

NST Engineering - ExamLens AI | Summer Profile Building Drive 2026
