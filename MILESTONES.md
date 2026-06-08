# Milestones

All 8 milestones with acceptance criteria and defense questions.
Framework: Build, Understand, Defend.

---

## M1: Project Scaffold and Document Ingestion

**Issues:** #1-4
**Duration:** Week 1

### Acceptance Criteria
- Repo has clean directory structure with all packages importable.
- PostgreSQL schema created via Alembic (users, exams, papers, questions, solutions, topics, mock_tests, study_plans tables).
- PDF upload endpoint accepts PDF and image files, extracts individual pages.
- User API supports student/contributor roles.
- Seed script populates database with sample data.
- At least 3 tests pass.

### Defense Questions
- Why PostgreSQL over SQLite for a project with full-text search needs?
- What is Alembic and why do we need versioned migrations?
- How does PyMuPDF extract pages from a PDF? What format are the output images?
- What validation do you perform on uploaded files (size, type, corruption)?
- How would you handle a 200-page PDF without running out of memory?

---

## M2: OCR and Text Extraction

**Issues:** #5-8
**Duration:** Week 2

### Acceptance Criteria
- Preprocessing pipeline handles deskew, denoise, and binarize on phone photos.
- Tesseract extracts printed text with > 90% accuracy on clean scans.
- EasyOCR fallback handles noisy/low-quality scans.
- TrOCR recognizes handwritten text with > 80% accuracy on clean handwriting.
- pix2tex converts math equations to valid LaTeX.
- All OCR outputs include confidence scores.
- At least 5 tests pass.

### Defense Questions
- How does adaptive thresholding differ from global thresholding? When is each better?
- Why Tesseract as primary and EasyOCR as fallback? When does each excel?
- How does TrOCR (transformer-based) differ architecturally from Tesseract (LSTM-based)?
- What is pix2tex doing under the hood to convert an image to LaTeX?
- How do you handle mixed content pages (text + equations + diagrams)?

---

## M3: Layout Detection and Question Parsing

**Issues:** #9-12
**Duration:** Week 3

### Acceptance Criteria
- Layout model detects question blocks, headers, marks indicators with > 80% mAP.
- Question splitter correctly separates individual questions from full pages.
- Metadata extractor identifies: question number, marks, sub-parts, question type.
- Multi-format parser handles MCQ, subjective, numerical, and mixed papers.
- Correction interface allows users to fix OCR errors before processing.
- At least 5 tests pass.

### Defense Questions
- Why YOLOv8 for layout detection? How is it different from LayoutLMv3?
- How do you train a layout detector with only 50-100 annotated papers?
- What heuristics help when the layout model fails (no marks shown, unusual formatting)?
- How do you handle papers that mix MCQ and subjective in the same section?
- What is mAP and why is it the standard metric for object detection?

---

## M4: Topic Tagging and Question Bank

**Issues:** #13-16
**Duration:** Week 4

### Acceptance Criteria
- Syllabus ingestion extracts a topic tree from uploaded syllabus PDF/text.
- Topic tagger maps questions to syllabus topics with > 85% accuracy.
- Question bank supports full-text search with filters (topic, year, type, marks).
- Deduplicator identifies same/paraphrased questions across years.
- At least 4 tests pass.

### Defense Questions
- How does the LLM map a question to a syllabus topic? What is the prompt structure?
- What is full-text search in PostgreSQL (tsvector/tsquery)? How does it differ from LIKE?
- How do you detect that two differently-worded questions are asking the same thing?
- What happens when a question spans multiple topics?
- How would you handle a syllabus that changes between years?

---

## M5: Answer Generation and Verification

**Issues:** #17-20
**Duration:** Week 5

### Acceptance Criteria
- Answer generator produces step-by-step solutions for MCQ, numerical, and subjective questions.
- Solutions include LaTeX-rendered equations where applicable.
- Verifier cross-checks against official answer keys when available.
- Quality scorer rates each solution as high/medium/low confidence.
- Answer display renders LaTeX correctly with step highlighting.
- At least 4 tests pass.

### Defense Questions
- How do you prompt the LLM to generate step-by-step solutions vs just the answer?
- What makes a "high confidence" vs "low confidence" answer?
- How does the verifier work when no official answer key exists?
- How do you handle questions that require diagrams in the solution?
- What is the risk of LLM hallucination in answer generation? How do you mitigate it?

---

## M6: Frequency Analysis and Prediction

**Issues:** #21-23
**Duration:** Week 6

### Acceptance Criteria
- Topic-year matrix correctly counts question appearances per topic per year.
- Trend detector identifies rising, falling, stable, and cyclic patterns.
- Prediction agent ranks topics by probability with explainable scoring.
- Heatmap visualization is interactive and exportable.
- At least 3 tests pass.

### Defense Questions
- What statistical method do you use for trend detection?
- How do you detect cyclic patterns (topic appears every 2-3 years)?
- How do you weight recency vs frequency in prediction scoring?
- What is the difference between a heatmap and a simple frequency table?
- How would you validate that your predictions actually match real exams?

---

## M7: Mock Paper Generator and Study Planner

**Issues:** #24-27
**Duration:** Week 7

### Acceptance Criteria
- Mock generator creates papers matching real exam pattern (marks distribution, question types, difficulty).
- Mock test interface supports timer, auto-save, and instant grading for MCQs.
- Study planner generates daily plans prioritized by topic importance and student weakness.
- Progress tracker shows improvement across mocks and topic coverage.
- At least 4 tests pass.

### Defense Questions
- How do you ensure generated mocks match the real exam pattern (not just random questions)?
- How do you estimate question difficulty without labeled difficulty data?
- What makes a study plan "personalized"? What signals does it use?
- How do you auto-grade subjective answers?
- What is the feedback loop between mock performance and study plan updates?

---

## M8: Dashboard, Scraper, and Demo

**Issues:** #28-30
**Duration:** Week 8

### Acceptance Criteria
- Scraper successfully fetches papers from at least 3 university/exam sources.
- Dashboard shows: question bank, topic analytics, mock tests, study plan.
- Mobile-responsive (375px+) with PWA for home screen installation.
- E2E test processes 5 sample papers through full pipeline without errors.
- Deployed to Railway/Render with live URL.
- Demo video (3-5 minutes) shows complete flow.
- All existing tests pass.

### Defense Questions
- How does Playwright handle JS-rendered university websites vs static HTML?
- What ethical/legal considerations apply to scraping university websites?
- How would you scale the scraper to handle 100+ universities?
- What is a PWA and why is it better than a native app for this use case?
- If you had 2 more weeks, what would you build next?

---

NST Engineering - ExamLens AI | Summer Profile Building Drive 2026
