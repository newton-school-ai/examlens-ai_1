# Development Guide

Full setup from scratch, daily workflow, and testing guide for ExamLens AI.

---

## Prerequisites

- Python 3.10+
- PostgreSQL 14+
- Node.js 18+ and npm
- Tesseract OCR
- Git + GitHub CLI (`gh`)

### Install Tesseract OCR

**macOS:**
```bash
brew install tesseract
brew install tesseract-lang  # for Hindi support
```

**Ubuntu/Debian:**
```bash
sudo apt install tesseract-ocr tesseract-ocr-hin
```

---

## Setup

### 1. Clone and create environment

```bash
git clone git@github.com:newton-school-ai/examlens-ai.git
cd examlens-ai
git checkout dev
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Environment variables

```bash
cp .env.example .env
# Edit .env: add your GROQ_API_KEY (free at console.groq.com)
```

### 3. Database

```bash
createdb examlens_dev
alembic upgrade head
python scripts/seed.py
```

### 4. Install Playwright browsers (for scraper)

```bash
playwright install chromium
```

### 5. Start backend

```bash
uvicorn src.api.main:app --reload
# API docs at http://localhost:8000/docs
```

### 6. Start frontend

```bash
cd frontend
npm install
npm run dev
# Dashboard at http://localhost:5173
```

---

## Daily Workflow

```bash
git checkout dev
git pull origin dev
git checkout -b feature/issue-6-tesseract-ocr

# ... write code ...
# ... write tests ...

pytest tests/ -v
black src/ tests/
isort src/ tests/
flake8 src/ tests/

git add -A
git commit -m "feat(ocr): integrate Tesseract for printed text extraction"
git push origin feature/issue-6-tesseract-ocr
# Open PR targeting dev on GitHub
```

---

## Testing

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_ocr_printed.py -v

# Run with coverage
pytest tests/ --cov=src --cov-report=term-missing
```

### Testing OCR locally

```bash
# Test with a sample PDF
python -c "
from src.ingestion.pdf_handler import extract_pages
pages = extract_pages('data/sample_papers/sample_gate_cs.pdf')
print(f'Extracted {len(pages)} pages')
"

# Test OCR on an image
python -c "
from src.cv.ocr_printed import extract_text
text = extract_text('data/sample_papers/page_1.png')
print(text[:500])
"
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `tesseract not found` | Install: `brew install tesseract` or `apt install tesseract-ocr` |
| `GROQ_API_KEY not set` | Get free key at console.groq.com, add to .env |
| `alembic upgrade head` fails | Check DATABASE_URL in .env, ensure PostgreSQL is running |
| `playwright` errors | Run `playwright install chromium && playwright install-deps` |
| Poor OCR quality | Check image preprocessing: `python -m src.cv.preprocessing --demo` |

---

NST Engineering - ExamLens AI | Summer Profile Building Drive 2026
