# Issues Tracker

All 30 issues with: Why, What, Files to create, How to test, Acceptance Criteria, Dependencies.

---

## M1: Project Scaffold and Document Ingestion

### Issue 1 - Initialize repo scaffold, CI workflow, Docker setup
**Why:** Clean, importable project structure from day one. Docker ensures reproducible environments.
**What:** Directory tree, __init__.py files, CI workflow, Docker config.
**Files:** All __init__.py, .github/workflows/ci.yml, Dockerfile, docker-compose.yml
**Test:** `python -c "from src.agents import supervisor"` + `docker-compose build`
**Acceptance:** All packages importable, CI runs on PRs, Docker builds cleanly.
**Depends on:** None.

### Issue 2 - Design database schema, Alembic migrations, and seed data
**Why:** Schema defines all data relationships. Alembic tracks schema evolution. Seed data accelerates development.
**What:** SQLAlchemy models, Alembic config, initial migration, seed script.
**Files:** src/models/*.py, alembic/, scripts/seed.py
**Test:** `alembic upgrade head` + `python scripts/seed.py`
**Acceptance:** 8 tables created, seed data populated, migration reversible.
**Depends on:** #1

### Issue 3 - Build PDF/image upload API and page extraction pipeline
**Why:** Entry point for all papers. Must handle PDFs, phone photos, and scanned images.
**What:** Upload endpoint, PDF page extraction via PyMuPDF, image validation.
**Files:** src/ingestion/*.py, src/api/routes/upload.py
**Test:** Upload a multi-page PDF, verify pages extracted as images.
**Acceptance:** PDF and image upload working, pages extracted, stored in DB.
**Depends on:** #2

### Issue 4 - Build user auth with Google OAuth, JWT sessions, and exam/paper management API
**Why:** One-click Google login for zero signup friction. Role-based access (student/contributor) and exam/paper organization needed before any analysis.
**What:** Google OAuth integration, JWT token issuance/validation, protected route middleware, user profile, exam/paper CRUD endpoints, frontend login UI.
**Files:** src/api/routes/auth.py, src/api/middleware/auth.py, src/api/routes/users.py, src/api/routes/papers.py, frontend/src/components/GoogleLoginButton.jsx, frontend/src/contexts/AuthContext.jsx
**Test:** Google login flow, JWT validation, protected route returns 401, role-based access, exam CRUD.
**Acceptance:** Student/contributor roles, exam CRUD, paper linked to exam.
**Depends on:** #2

---

## M2: OCR and Text Extraction

### Issue 5 - Build image preprocessing pipeline
**Why:** Raw phone photos are noisy, rotated, poorly lit. Preprocessing is essential for OCR accuracy.
**What:** Deskew, denoise, binarize, contrast enhancement pipeline.
**Files:** src/cv/preprocessing.py
**Test:** Process a tilted phone photo, verify straightened output.
**Acceptance:** Handles rotation, noise, low contrast. Measurable accuracy improvement.
**Depends on:** #3

### Issue 6 - Integrate Tesseract and EasyOCR for printed text
**Why:** Printed text is the primary OCR target. Tesseract is fast/free, EasyOCR handles noisy scans better.
**What:** Tesseract integration with EasyOCR fallback, confidence scoring.
**Files:** src/cv/ocr_printed.py
**Test:** OCR a sample GATE paper, compare output to ground truth.
**Acceptance:** >90% accuracy on clean scans, >80% on noisy. Confidence scores included.
**Depends on:** #5

### Issue 7 - Integrate TrOCR for handwritten text
**Why:** Some university papers are handwritten. TrOCR is SOTA for handwriting recognition.
**What:** TrOCR model integration, line segmentation, text extraction.
**Files:** src/cv/ocr_handwritten.py
**Test:** Process a handwritten page, verify extracted text.
**Acceptance:** >80% accuracy on clean handwriting, confidence scores included.
**Depends on:** #5

### Issue 8 - Build math equation extractor
**Why:** JEE/GATE/university math papers have equations that Tesseract cannot handle. pix2tex specializes in this.
**What:** pix2tex integration, equation region detection, LaTeX output.
**Files:** src/cv/math_extractor.py
**Test:** Extract equations from a JEE Math paper, verify valid LaTeX.
**Acceptance:** Valid LaTeX output, renders correctly in KaTeX/MathJax.
**Depends on:** #5

---

## M3: Layout Detection and Question Parsing

### Issue 9 - Train layout detection model for question paper structure
**Why:** Must identify question blocks, headers, marks before parsing. Different papers have different layouts.
**What:** YOLOv8 fine-tuning on annotated question papers, inference pipeline.
**Files:** src/cv/layout_detector.py, notebooks/layout_training.ipynb
**Test:** Run on sample paper, verify bounding boxes around question blocks.
**Acceptance:** >80% mAP on test set, detects questions/headers/marks.
**Depends on:** #6

### Issue 10 - Build question splitter and metadata extractor
**Why:** A full page of OCR text is useless - must be split into individual questions with metadata.
**What:** Split OCR output into questions, extract number/marks/type/sub-parts.
**Files:** src/parsing/question_parser.py, src/parsing/metadata_extractor.py, src/parsing/question_splitter.py
**Test:** Process a full paper, verify each question parsed with correct metadata.
**Acceptance:** Correct question count, marks allocation, sub-part detection.
**Depends on:** #9

### Issue 11 - Handle multi-format papers (MCQ, subjective, numerical, mixed)
**Why:** Different exams use different formats. JEE is MCQ, GATE mixes MCQ+numerical, university is subjective.
**What:** Format detection, type-specific parsing logic.
**Files:** src/parsing/question_parser.py (extend)
**Test:** Process JEE (MCQ), GATE (mixed), university (subjective) papers.
**Acceptance:** Correctly identifies question type for each format.
**Depends on:** #10

### Issue 12 - Build OCR confidence scorer and correction interface
**Why:** OCR is never 100% accurate. Users need to see and fix errors before analysis runs.
**What:** Confidence scoring per text block, frontend correction UI.
**Files:** src/cv/confidence_scorer.py, frontend/src/components/CorrectionUI.jsx
**Test:** Upload a noisy scan, verify low-confidence blocks are highlighted.
**Acceptance:** Low confidence text flagged, editable, corrections saved.
**Depends on:** #6, #10

---

## M4: Topic Tagging and Question Bank

### Issue 13 - Build syllabus ingestion system
**Why:** Topic tagging needs a reference. The syllabus defines what topics exist for a course.
**What:** Upload syllabus PDF/text, extract topic tree with hierarchy (unit > topic > subtopic).
**Files:** src/agents/syllabus_parser.py, src/api/routes/syllabus.py
**Test:** Upload a GATE CS syllabus, verify topic tree extracted.
**Acceptance:** Hierarchical topic tree, linked to exam/course, searchable.
**Depends on:** #2

### Issue 14 - Build LLM-based topic tagger agent
**Why:** Manually tagging thousands of questions is impractical. LLM maps questions to syllabus topics.
**What:** LangGraph agent that takes question text + syllabus and returns topic tags.
**Files:** src/agents/topic_tagger.py
**Test:** Tag 50 questions from a GATE CS paper, verify >85% match manual tags.
**Acceptance:** >85% accuracy, handles multi-topic questions, uses syllabus as reference.
**Depends on:** #10, #13

### Issue 15 - Build searchable question bank with full-text search
**Why:** The question bank is the core product. Students must find questions by topic/year/type instantly.
**What:** PostgreSQL full-text search, API with filters, paginated results.
**Files:** src/api/routes/questions.py, frontend/src/components/QuestionBank.jsx
**Test:** Search "binary tree traversal", filter by year=2024, type=MCQ.
**Acceptance:** Full-text search works, filters combine correctly, pagination.
**Depends on:** #14

### Issue 16 - Implement question deduplication
**Why:** Same questions appear across years (often paraphrased). Duplicates skew frequency analysis.
**What:** LLM-based similarity detection, duplicate grouping, canonical question selection.
**Files:** src/parsing/deduplicator.py
**Test:** Feed 3 paraphrased versions of same question, verify grouped as duplicates.
**Acceptance:** Detects exact and paraphrased duplicates, groups them, picks canonical.
**Depends on:** #14

---

## M5: Answer Generation and Verification

### Issue 17 - Build answer generator agent
**Why:** The killer feature. Step-by-step solutions with explanations, not just "option B".
**What:** LangGraph agent that generates solutions based on question type (MCQ, numerical, subjective).
**Files:** src/agents/answer_generator.py
**Test:** Generate solutions for 20 GATE questions, verify step-by-step logic.
**Acceptance:** Solutions include steps, explanations, LaTeX for equations. Handles MCQ/numerical/subjective.
**Depends on:** #14

### Issue 18 - Implement answer verifier agent
**Why:** LLM-generated answers can be wrong. Verification against official keys catches errors.
**What:** Cross-check agent that compares generated answers against official keys and multiple sources.
**Files:** src/agents/answer_verifier.py
**Test:** Verify 20 JEE answers against NTA official key, measure match rate.
**Acceptance:** Correctly verifies against official keys, flags mismatches, confidence scoring.
**Depends on:** #17

### Issue 19 - Add solution quality scorer and confidence rating
**Why:** Students need to know how much to trust each solution. High/medium/low confidence guides study.
**What:** Scoring based on: verified against key (high), LLM confident (medium), uncertain (low).
**Files:** src/agents/quality_scorer.py
**Test:** Score 30 solutions, verify high-confidence ones match official answers.
**Acceptance:** 3-tier confidence, verified answers = high, flagged answers visible to user.
**Depends on:** #18

### Issue 20 - Build answer display UI with LaTeX rendering
**Why:** Math solutions are unreadable without proper rendering. Step highlighting aids understanding.
**What:** React component with KaTeX/MathJax rendering, collapsible steps, confidence badge.
**Files:** frontend/src/components/SolutionDisplay.jsx, frontend/src/components/LaTeXRenderer.jsx
**Test:** Display a JEE Math solution with integrals, verify LaTeX renders correctly.
**Acceptance:** LaTeX renders correctly, steps collapsible, confidence badge shown, mobile-friendly.
**Depends on:** #17

---

## M6: Frequency Analysis and Prediction

### Issue 21 - Build topic frequency analyzer with trend detection
**Why:** "What comes every year?" is the #1 question students ask. This answers it with data.
**What:** Topic-year matrix, frequency counts, trend detection (rising/falling/stable/cyclic).
**Files:** src/analysis/frequency_analyzer.py, src/analysis/trend_detector.py
**Test:** Analyze 5 years of GATE CS papers, verify frequency matches manual count.
**Acceptance:** Correct frequency counts, trend classification, handles missing years.
**Depends on:** #14

### Issue 22 - Build exam prediction agent
**Why:** Students want to know what to study. Prediction ranks topics by likelihood of appearing.
**What:** LangGraph agent combining frequency, trends, recency, and gap analysis.
**Files:** src/agents/prediction_agent.py, src/analysis/importance_scorer.py
**Test:** Predict top 10 topics for GATE 2027 based on 2020-2026 data.
**Acceptance:** Ranked topic list with scores, explainable reasoning, handles sparse data.
**Depends on:** #21

### Issue 23 - Create analytics visualization
**Why:** Numbers alone are hard to interpret. Heatmaps and charts make patterns visible instantly.
**What:** Topic frequency heatmap, trend charts, marks distribution, exportable reports.
**Files:** frontend/src/components/TopicHeatmap.jsx, frontend/src/components/TrendChart.jsx, src/api/routes/analytics.py
**Test:** View heatmap for GATE CS, verify hovering shows details, export as CSV.
**Acceptance:** Interactive heatmap, trend line charts, CSV/JSON export, responsive.
**Depends on:** #21

---

## M7: Mock Paper Generator and Study Planner

### Issue 24 - Build mock paper generator agent
**Why:** Practice with realistic mocks is more valuable than random question sets.
**What:** LangGraph agent that creates mock papers matching real exam patterns.
**Files:** src/agents/mock_generator.py, src/mock/paper_generator.py
**Test:** Generate a GATE CS mock, compare structure to real GATE paper.
**Acceptance:** Matches marks distribution, question types, topic coverage, difficulty mix.
**Depends on:** #21

### Issue 25 - Build mock test taking interface with auto-grading
**Why:** Students need to practice under exam conditions. Timer + instant grading enables this.
**What:** Test interface with timer, question navigation, auto-save, MCQ auto-grading.
**Files:** frontend/src/pages/MockTest.jsx, src/api/routes/mock.py, src/mock/grader.py
**Test:** Take a 10-question mock, verify timer works, score calculated correctly.
**Acceptance:** Timer, question navigation, auto-save on disconnect, instant MCQ grading.
**Depends on:** #24

### Issue 26 - Build personalized study plan agent
**Why:** A ranked topic list is not a study plan. Students need daily actionable plans.
**What:** LangGraph agent that generates daily study plans based on exam date, weak topics, available time.
**Files:** src/agents/study_planner.py, src/api/routes/study.py
**Test:** Generate a 30-day plan for GATE CS, verify it prioritizes weak topics.
**Acceptance:** Daily plan with topics + estimated time, prioritizes weak areas, adjustable.
**Depends on:** #22, #25

### Issue 27 - Add progress tracker
**Why:** Students need to see they are improving. Visible progress sustains motivation.
**What:** Track topics studied, mock scores over time, weak area identification.
**Files:** src/mock/progress_tracker.py, frontend/src/components/ProgressDashboard.jsx
**Test:** Take 3 mocks, verify score trend chart and weak topic identification.
**Acceptance:** Score trend chart, topic coverage percentage, weak areas highlighted.
**Depends on:** #25

---

## M8: Dashboard, Scraper, and Demo

### Issue 28 - Build PYQ scraper agent
**Why:** Students should not have to find and upload papers manually. Scraper fetches them automatically.
**What:** Playwright-based scraper for university sites and exam portals, rate-limited, respectful.
**Files:** src/agents/scraper_agent.py
**Test:** Scrape GATE CS papers from gate.iitk.ac.in, verify PDFs downloaded.
**Acceptance:** Fetches from 3+ sources, respects rate limits, handles JS-rendered sites.
**Depends on:** #3

### Issue 29 - Build student dashboard with mobile-responsive PWA
**Why:** Single interface for all features. PWA lets students access on phone without app store.
**What:** React dashboard with question bank, analytics, mocks, study plan. PWA manifest + service worker.
**Files:** frontend/src/pages/Dashboard.jsx, frontend/public/manifest.json, frontend/public/service-worker.js
**Test:** Open on phone (375px), verify all sections usable, add to home screen.
**Acceptance:** All features accessible, responsive, PWA installable, Lighthouse > 80.
**Depends on:** #15, #20, #23, #25, #27

### Issue 30 - E2E testing, deployment, demo video
**Why:** Proves the full pipeline works. Live URL for recruiters. Demo video for portfolio.
**What:** E2E tests, Docker deployment to Railway/Render, demo video script.
**Files:** tests/test_e2e.py, docs/deployment_guide.md, docs/architecture.md, docs/demo_script.md
**Test:** `pytest tests/test_e2e.py` + `docker-compose up` + verify live URL.
**Acceptance:** E2E passes, live URL accessible, demo video recorded (3-5 min).
**Depends on:** #29

---

NST Engineering - ExamLens AI | Summer Profile Building Drive 2026
