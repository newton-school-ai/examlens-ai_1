#!/bin/bash
# ExamLens AI - Create all 30 issues on GitHub (milestones already exist)
# Usage: cd examlens-ai && bash scripts/create_github_issues.sh

set -e

REPO="newton-school-ai/examlens-ai"

echo "========================================="
echo "Creating 30 issues for $REPO"
echo "========================================="

echo ""
echo ">>> Fetching existing milestone titles..."

# Verify milestones exist
gh api repos/$REPO/milestones --jq '.[].title' | sort

echo ""
echo "All 8 milestones found. Proceeding to create issues..."
echo ""

# Milestone titles (must match exactly what's on GitHub)
M1="M1: Project Scaffold and Document Ingestion"
M2="M2: OCR and Text Extraction"
M3="M3: Layout Detection and Question Parsing"
M4="M4: Topic Tagging and Question Bank"
M5="M5: Answer Generation and Verification"
M6="M6: Frequency Analysis and Prediction"
M7="M7: Mock Paper Generator and Study Planner"
M8="M8: Dashboard, Scraper, and Demo"

# ─── Helper ────────────────────────────────────────────────────────────────

echo ""
echo ">>> Creating issues..."

create_issue() {
  local num="$1"
  local title="$2"
  local milestone="$3"
  local labels="$4"
  local body="$5"

  local full_title="Issue $num - $title"
  echo -n "  #$num $full_title ... "
  gh issue create --repo "$REPO" \
    --title "$full_title" \
    --milestone "$milestone" \
    --label "$labels" \
    --body "$body" > /dev/null 2>&1
  echo "✓"
  sleep 1
}

# ─── M1 Issues (#1-4) ─────────────────────────────────────────────────────

create_issue 1 "Initialize repo scaffold, CI workflow, Docker setup" "$M1" "m1,infra" \
"## Why

Before anyone writes OCR code or trains a layout model, the project needs a clean structure that every contributor can clone and immediately work in. Without this, four contributors create four different directory layouts, import paths break, and merging becomes a nightmare.

CI is included because it enforces coding standards automatically. When four contributors each submit competitive PRs, the Maintainer needs a quick way to verify all submissions pass basic quality checks. Docker ensures the development environment is reproducible - Tesseract, EasyOCR, Playwright, and PyMuPDF all have system-level dependencies that differ between macOS and Linux.

## What needs to be built

Full directory tree with Python packages, GitHub Actions CI workflow, Docker and docker-compose configuration.

## Files to create or update

- All \`__init__.py\` files in \`src/\` subdirectories
- \`.github/workflows/ci.yml\` - CI workflow
- \`Dockerfile\` - with Tesseract and system deps
- \`docker-compose.yml\` - backend + PostgreSQL + frontend
- Verify \`requirements.txt\` installs cleanly
- Verify \`.gitignore\` covers generated files

## How this affects overall development

Every other issue depends on this. If the scaffold is wrong, every contributor's work is built on a broken foundation. CI catches broken code before review. Docker ensures \"works on my machine\" is never an excuse.

## How to test locally

\`\`\`bash
git clone https://github.com/newton-school-ai/examlens-ai.git
cd examlens-ai
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

python -c \"from src.agents import supervisor; print('agents OK')\"
python -c \"from src.cv import preprocessing; print('cv OK')\"
python -c \"from src.parsing import question_parser; print('parsing OK')\"
python -c \"from src.analysis import frequency_analyzer; print('analysis OK')\"
python -c \"from src.api import main; print('api OK')\"

docker-compose build
docker-compose up -d
curl http://localhost:8000/health
\`\`\`

## Acceptance Criteria

- [ ] All \`src/\` packages importable without errors
- [ ] \`pip install -r requirements.txt\` succeeds in clean virtualenv
- [ ] GitHub Actions CI runs black --check, isort --check, flake8, pytest on every PR
- [ ] CI completes in under 3 minutes
- [ ] \`docker-compose build\` succeeds (Tesseract installed in container)
- [ ] \`docker-compose up\` starts backend + PostgreSQL + frontend
- [ ] \`.gitignore\` covers: .env, __pycache__, data/*.pdf, models/weights/, _internal/

## Branch

\`feature/issue-1-scaffold\`

## Depends on

None (first issue)"

create_issue 2 "Design database schema, Alembic migrations, and seed data" "$M1" "m1,infra" \
"## Why

ExamLens stores papers, extracted questions, solutions, topic mappings, mock tests, and study plans. The schema defines how these relate: a Paper belongs to an Exam, a Question belongs to a Paper, a Solution belongs to a Question, a Topic maps to many Questions. Getting these relationships wrong means rewriting queries, endpoints, and UI components later.

Alembic migrations track schema changes. When issue #19 adds a confidence column to solutions, that change propagates to every contributor's database without data loss. The seed script gives every contributor identical test data - sample exams, papers, questions, and topics to develop against.

## What needs to be built

SQLAlchemy models for all 8 core tables, Alembic config, initial migration, and seed script.

## Files to create or update

- \`src/models/user.py\` - User (student/contributor roles)
- \`src/models/exam.py\` - Exam (type, name, year)
- \`src/models/paper.py\` - Paper (PDF path, page count, exam FK)
- \`src/models/question.py\` - Question (text, marks, type, number, paper FK)
- \`src/models/solution.py\` - Solution (steps, answer, confidence, question FK)
- \`src/models/topic.py\` - Topic (name, parent FK for hierarchy, exam FK)
- \`src/models/mock_test.py\` - MockTest (generated paper, user FK)
- \`src/models/study_plan.py\` - StudyPlan (daily plan, user FK)
- \`alembic/\` - Config and initial migration
- \`scripts/seed.py\` - Sample data

## How this affects overall development

Every API endpoint reads from or writes to these tables. The question bank (#15) queries questions. The answer generator (#17) writes solutions. The frequency analyzer (#21) aggregates from questions. Wrong schema = rewrite everything downstream.

## How to test locally

\`\`\`bash
createdb examlens_dev
alembic upgrade head

python -c \"
from sqlalchemy import create_engine, inspect
engine = create_engine('postgresql://localhost/examlens_dev')
tables = inspect(engine).get_table_names()
print(f'Tables: {tables}')
assert 'users' in tables
assert 'questions' in tables
assert 'solutions' in tables
print('All tables created')
\"

python scripts/seed.py

alembic downgrade base
\`\`\`

## Acceptance Criteria

- [ ] 8 SQLAlchemy models with correct columns, types, foreign keys, relationships
- [ ] Question model stores: text, marks, type (MCQ/subjective/numerical), number, sub-parts, year
- [ ] Solution model stores: steps (JSON list), final_answer, confidence (high/medium/low), LaTeX content
- [ ] Topic model supports hierarchy (parent_id self-reference for unit > topic > subtopic)
- [ ] \`alembic upgrade head\` creates all tables
- [ ] \`alembic downgrade base\` removes all tables cleanly
- [ ] Seed script creates realistic sample data (is idempotent)
- [ ] At least 3 tests: model creation, relationships, constraints

## Branch

\`feature/issue-2-db-schema\`

## Depends on

Closes #1"

create_issue 3 "Build PDF/image upload API and page extraction pipeline" "$M1" "m1,infra,cv" \
"## Why

Everything in ExamLens starts with a document. Students upload PYQ PDFs, phone photos of printed papers, or scanned images. The ingestion pipeline must handle all of these, extract individual pages as images, and store them for downstream OCR processing.

PyMuPDF (fitz) is chosen for PDF processing because it is fast, handles corrupted PDFs gracefully, and can extract pages as high-resolution images (300 DPI) suitable for OCR. For phone photos, the pipeline validates the image, checks resolution, and stores it as a single \"page.\"

## What needs to be built

Upload API endpoint, PDF page extraction via PyMuPDF, image validation, storage.

## Files to create or update

- \`src/ingestion/pdf_handler.py\` - PDF processing with PyMuPDF
- \`src/ingestion/image_handler.py\` - Image validation and storage
- \`src/ingestion/page_extractor.py\` - Extract pages as images
- \`src/api/routes/upload.py\` - Upload endpoint

## How this affects overall development

This is the data entry point. Every downstream module (OCR, parsing, analysis) starts with pages extracted by this pipeline. If page extraction produces blurry or incorrectly rotated images, OCR accuracy suffers for every paper.

## How to test locally

\`\`\`bash
uvicorn src.api.main:app --reload

curl -X POST http://localhost:8000/api/upload \\
  -F \"file=@data/sample_papers/sample_gate_cs.pdf\" \\
  -F \"exam_id=1\"

curl -X POST http://localhost:8000/api/upload \\
  -F \"file=@data/sample_papers/phone_photo.jpg\" \\
  -F \"exam_id=1\"

curl http://localhost:8000/api/papers/1/pages
\`\`\`

## Acceptance Criteria

- [ ] POST /api/upload accepts PDF and image files (JPG, PNG)
- [ ] PDF pages extracted as 300 DPI PNG images via PyMuPDF
- [ ] Phone photos validated for minimum resolution (640x480)
- [ ] Rejects files > 50MB with clear error message
- [ ] Rejects non-PDF/non-image files with clear error message
- [ ] Paper record created in database with page count
- [ ] Pages stored in data/papers/{paper_id}/ directory
- [ ] At least 3 tests: PDF upload, image upload, invalid file rejection

## Branch

\`feature/issue-3-upload-pipeline\`

## Depends on

Closes #2"

create_issue 4 "Build user auth with Google OAuth, JWT sessions, and exam/paper management API" "$M1" "m1,infra,frontend" \
"## Why

ExamLens needs to track who uploaded which papers, who took which mock tests, and whose study plan is whose. The user system supports two roles: students (consume content) and contributors (upload and verify papers, earning contribution scores).

Google OAuth is the primary login method because the target users are Indian college students - almost all of them have a Google account (university email or personal Gmail). No one wants to create yet another username/password. One-click Google login reduces signup friction to near zero, which matters for adoption.

The flow: student clicks \"Sign in with Google\" -> Google consent screen -> backend receives auth code -> exchanges for Google profile (name, email, avatar) -> creates or finds user in database -> issues a JWT token for session management. JWTs are used because the frontend is a React SPA - stateless tokens avoid server-side session storage.

Exam and paper management endpoints let users organize papers by exam type and year. \"Show me all GATE CS papers from 2020-2025\" requires structured exam/paper relationships, not a flat file dump.

## What needs to be built

Google OAuth integration, JWT token issuance/validation, protected route middleware, user registration/login, exam CRUD, paper management endpoints, frontend login UI.

## Files to create or update

- \`src/api/routes/auth.py\` - Google OAuth callback, token issuance, token refresh
- \`src/api/routes/users.py\` - User profile, role management
- \`src/api/routes/papers.py\` - Paper listing, filtering by exam
- \`src/api/middleware/auth.py\` - JWT verification middleware, role-based access (student vs contributor)
- \`src/api/schemas/user.py\` - Pydantic schemas (UserCreate, UserResponse, TokenResponse)
- \`src/models/user.py\` - Add google_id, avatar_url, auth_provider fields
- \`frontend/src/components/GoogleLoginButton.jsx\` - Google sign-in button using @react-oauth/google
- \`frontend/src/contexts/AuthContext.jsx\` - Auth state management, token storage, auto-refresh
- \`.env.example\` - Add GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, JWT_SECRET_KEY

## How this affects overall development

User identity gates mock test history (#25), study plans (#26), progress tracking (#27), and contribution scores (#12). Protected routes ensure only authenticated users can upload papers or take mocks. Exam/paper organization is needed before any analysis - the frequency analyzer needs to query \"all GATE CS papers from 2020-2025.\"

## How to test locally

\`\`\`bash
# 1. Set up Google OAuth credentials at console.cloud.google.com
#    - Create OAuth 2.0 Client ID (Web application)
#    - Add http://localhost:5173 to Authorized JavaScript origins
#    - Add http://localhost:8000/api/auth/google/callback to Authorized redirect URIs
#    - Copy Client ID and Client Secret to .env

# 2. Start backend
uvicorn src.api.main:app --reload

# 3. Start frontend
cd frontend && npm run dev

# 4. Click \"Sign in with Google\" -> consent screen -> redirected back -> logged in

# 5. Verify JWT works
TOKEN=\"<jwt_from_login_response>\"
curl -H \"Authorization: Bearer \$TOKEN\" http://localhost:8000/api/users/me

# 6. Test protected route without token
curl http://localhost:8000/api/users/me
# Should return 401 Unauthorized

# 7. Test exam management
curl -X POST http://localhost:8000/api/exams \\
  -H \"Authorization: Bearer \$TOKEN\" \\
  -H \"Content-Type: application/json\" \\
  -d '{\"name\": \"GATE CS\", \"type\": \"gate\", \"year\": 2025}'

curl http://localhost:8000/api/exams/1/papers
\`\`\`

## Acceptance Criteria

- [ ] Google OAuth login flow works end-to-end (click -> consent -> JWT -> logged in)
- [ ] Backend exchanges Google auth code for user profile (name, email, avatar)
- [ ] New users auto-created on first Google login with default role \"student\"
- [ ] JWT issued on login, expires in 24 hours, refresh token for 7 days
- [ ] JWT middleware protects routes: upload, mock test, study plan, profile edit
- [ ] Public routes remain accessible without auth: question bank search, analytics view
- [ ] GET /api/users/me returns authenticated user's profile
- [ ] Role-based access: contributor-only routes (paper upload, OCR correction) check role
- [ ] Frontend shows Google login button, user avatar + name after login, logout button
- [ ] Auth state persists across page refresh (token stored in memory, refresh on expiry)
- [ ] POST /api/exams creates exam with type and year
- [ ] GET /api/exams/{id}/papers lists papers for an exam
- [ ] GET /api/papers?exam_type=gate&year=2025 filters papers
- [ ] At least 5 tests: Google login mock, JWT validation, protected route 401, role check, exam CRUD

## Branch

\`feature/issue-4-user-exam-api\`

## Depends on

Closes #2"

# ─── M2 Issues (#5-8) ─────────────────────────────────────────────────────

create_issue 5 "Build image preprocessing pipeline" "$M2" "m2,cv" \
"## Why

Raw phone photos and scanned PDFs are noisy, tilted, poorly lit, and low contrast. Feeding these directly to OCR produces garbage. Preprocessing is the difference between 60% and 95% OCR accuracy.

Deskewing corrects rotation (a phone photo taken at an angle). Denoising removes scanner artifacts and compression noise. Binarization converts grayscale to black-and-white (what OCR models expect). CLAHE enhances contrast in unevenly lit photos (one corner is darker than another).

## What needs to be built

Image preprocessing pipeline with deskew, denoise, binarize, and contrast enhancement.

## Files to create or update

- \`src/cv/preprocessing.py\` - Full preprocessing pipeline

## How this affects overall development

Every OCR module (#6, #7, #8) receives preprocessed images. If preprocessing is poor, all three OCR engines produce poor results. This is the foundation of text extraction accuracy.

## How to test locally

\`\`\`bash
python -m src.cv.preprocessing --input data/sample_papers/tilted_photo.jpg --output preprocessed.png

python -c \"
from src.cv.preprocessing import preprocess_image
import cv2
img = cv2.imread('data/sample_papers/tilted_photo.jpg')
result = preprocess_image(img)
print(f'Input: {img.shape}, Output: {result.shape}')
\"

pytest tests/test_preprocessing.py -v
\`\`\`

## Acceptance Criteria

- [ ] Deskew corrects rotation up to 15 degrees
- [ ] Denoise removes scanner artifacts without losing text
- [ ] Binarize produces clean black-on-white output via adaptive thresholding
- [ ] CLAHE handles unevenly lit photos
- [ ] Pipeline is configurable (skip steps, adjust parameters)
- [ ] Processing time < 1 second per page on laptop CPU
- [ ] At least 4 tests: deskew, denoise, binarize, full pipeline

## Branch

\`feature/issue-5-preprocessing\`

## Depends on

Closes #3"

create_issue 6 "Integrate Tesseract and EasyOCR for printed text" "$M2" "m2,cv" \
"## Why

Printed text is the primary OCR target - most PYQ papers are printed. Tesseract 5 (LSTM engine) is fast, free, and handles clean scans well. EasyOCR is the fallback for noisy/low-quality scans where Tesseract struggles - it uses a deep learning approach that is more robust to noise but slower.

The dual-engine approach means: try Tesseract first (fast). If confidence is low, retry with EasyOCR (accurate on noise). This gives both speed on clean documents and accuracy on bad scans.

Post-processing is critical. OCR engines make predictable mistakes: 'l' vs '1', 'O' vs '0', 'rn' vs 'm'. A post-processing step with common error patterns and spell-checking catches these.

## What needs to be built

Tesseract integration with EasyOCR fallback, confidence scoring, and post-processing.

## Files to create or update

- \`src/cv/ocr_printed.py\` - Dual-engine OCR with fallback logic

## How this affects overall development

This is the primary text extraction engine. The question parser (#10) operates on this output. If OCR is inaccurate, every downstream module (parsing, tagging, answer generation) inherits those errors.

## How to test locally

\`\`\`bash
python -m src.cv.ocr_printed --input data/sample_papers/gate_cs_2024_page1.png

python -c \"
from src.cv.ocr_printed import extract_text_printed
result = extract_text_printed('data/sample_papers/gate_cs_2024_page1.png')
print(f'Engine: {result.engine}')
print(f'Confidence: {result.confidence:.2f}')
print(f'Text: {result.text[:300]}...')
\"

pytest tests/test_ocr_printed.py -v
\`\`\`

## Acceptance Criteria

- [ ] Tesseract extracts printed text with > 90% accuracy on clean scans
- [ ] EasyOCR fallback activates when Tesseract confidence < 0.7
- [ ] EasyOCR achieves > 80% accuracy on noisy scans
- [ ] Supports English and Hindi text (bilingual papers)
- [ ] Post-processing corrects common OCR errors (l/1, O/0, rn/m)
- [ ] Returns structured result: text, confidence, engine used, bounding boxes
- [ ] Processing time < 3 seconds per page (Tesseract), < 10 seconds (EasyOCR)
- [ ] At least 5 tests: clean scan, noisy scan, Hindi text, fallback trigger, post-processing

## Branch

\`feature/issue-6-printed-ocr\`

## Depends on

Closes #5"

create_issue 7 "Integrate TrOCR for handwritten text recognition" "$M2" "m2,cv" \
"## Why

Some university question papers are handwritten (especially supplementary exams and internal assessments). Students may also upload handwritten notes for analysis. Tesseract performs poorly on handwriting (< 50% accuracy). TrOCR (Microsoft's transformer-based model) achieves state-of-the-art results on handwritten text by treating OCR as an image-to-text sequence problem.

TrOCR requires line segmentation before recognition - it processes one text line at a time. The pipeline must detect text lines in the image, crop them, and feed each line to TrOCR individually.

## What needs to be built

TrOCR integration with line segmentation for handwritten text recognition.

## Files to create or update

- \`src/cv/ocr_handwritten.py\` - TrOCR pipeline with line segmentation

## How this affects overall development

Extends ExamLens to handwritten papers, which are common in Indian university internal exams. Without this, the system only works on printed papers.

## How to test locally

\`\`\`bash
python -m src.cv.ocr_handwritten --input data/sample_papers/handwritten_page.jpg

python -c \"
from src.cv.ocr_handwritten import extract_text_handwritten
result = extract_text_handwritten('data/sample_papers/handwritten_page.jpg')
print(f'Lines detected: {len(result.lines)}')
for line in result.lines[:5]:
    print(f'  [{line.confidence:.2f}] {line.text}')
\"

pytest tests/test_ocr_handwritten.py -v
\`\`\`

## Acceptance Criteria

- [ ] TrOCR model loads and runs on CPU (no GPU required)
- [ ] Line segmentation detects text lines in handwritten pages
- [ ] > 80% accuracy on clean handwriting
- [ ] Confidence score per line (low confidence lines flagged for correction)
- [ ] Handles mixed handwritten + printed pages (detects which is which)
- [ ] Processing time < 15 seconds per page on CPU
- [ ] At least 3 tests: clean handwriting, messy handwriting, mixed page

## Branch

\`feature/issue-7-handwritten-ocr\`

## Depends on

Closes #5"

create_issue 8 "Build math equation extractor (image to LaTeX)" "$M2" "m2,cv" \
"## Why

JEE Math, GATE Engineering Math, and university physics/math papers are full of equations that Tesseract and EasyOCR cannot handle. An integral sign becomes garbled text. A fraction becomes two separate lines.

pix2tex is a specialized model trained specifically to convert images of math equations into LaTeX strings. The LaTeX can then be rendered in the frontend using KaTeX, making solutions readable.

The pipeline must first detect equation regions in a page (not everything is math), crop them, run pix2tex on each region, and embed the LaTeX back into the extracted text at the correct position.

## What needs to be built

pix2tex integration with equation region detection and LaTeX output.

## Files to create or update

- \`src/cv/math_extractor.py\` - Equation detection and LaTeX extraction

## How this affects overall development

The answer generator (#17) includes LaTeX in solutions. The answer display (#20) renders LaTeX. Without reliable equation extraction, math-heavy papers lose their most important content.

## How to test locally

\`\`\`bash
python -m src.cv.math_extractor --input data/sample_papers/jee_math_page.png

python -c \"
from src.cv.math_extractor import extract_equations
results = extract_equations('data/sample_papers/jee_math_page.png')
for eq in results:
    print(f'Equation at ({eq.x}, {eq.y}): {eq.latex}')
\"

pytest tests/test_math_extractor.py -v
\`\`\`

## Acceptance Criteria

- [ ] Detects equation regions in mixed text+math pages
- [ ] Converts equation images to valid LaTeX strings
- [ ] Handles: fractions, integrals, summations, matrices, Greek symbols, superscripts/subscripts
- [ ] LaTeX output renders correctly in KaTeX (verify with online renderer)
- [ ] Confidence score per equation
- [ ] Processing time < 5 seconds per equation on CPU
- [ ] At least 4 tests: simple equation, complex equation (integral), matrix, inline math

## Branch

\`feature/issue-8-math-extractor\`

## Depends on

Closes #5"

# ─── M3 Issues (#9-12) ────────────────────────────────────────────────────

create_issue 9 "Train layout detection model for question paper structure" "$M3" "m3,cv" \
"## Why

A raw OCR dump of a full page is a wall of text with no structure. The layout detector identifies where each question starts and ends, where marks are indicated, where headers and page numbers are. This structure is essential before the question parser can split the page into individual questions.

YOLOv8 is chosen because layout detection is fundamentally an object detection problem - find bounding boxes around question blocks, marks indicators, headers, and diagrams. YOLOv8 is fast, accurate, and requires relatively few annotated examples for fine-tuning (50-100 papers).

## What needs to be built

YOLOv8 fine-tuning on annotated question papers, inference pipeline.

## Files to create or update

- \`src/cv/layout_detector.py\` - Layout detection inference pipeline
- \`notebooks/layout_training.ipynb\` - Training notebook with annotation guide

## How this affects overall development

The question splitter (#10) uses layout detection to identify question boundaries. Without accurate layout detection, the splitter cannot tell where one question ends and the next begins.

## How to test locally

\`\`\`bash
python -m src.cv.layout_detector --input data/sample_papers/gate_cs_2024_page1.png

python -c \"
from src.cv.layout_detector import detect_layout
results = detect_layout('data/sample_papers/gate_cs_2024_page1.png')
for block in results:
    print(f'{block.label}: confidence={block.confidence:.2f}, bbox={block.bbox}')
\"

pytest tests/test_layout_detector.py -v
\`\`\`

## Acceptance Criteria

- [ ] Detects classes: question_block, marks_indicator, header, page_number, diagram, table
- [ ] > 80% mAP on test set of annotated papers
- [ ] Training notebook runs end-to-end with annotation instructions
- [ ] Handles different paper formats (single column, double column, MCQ grid)
- [ ] Inference time < 2 seconds per page on CPU
- [ ] Exports trained weights to \`models/weights/layout_detector.pt\`
- [ ] At least 4 tests: single column, double column, MCQ format, marks detection

## Branch

\`feature/issue-9-layout-detector\`

## Depends on

Closes #6"

create_issue 10 "Build question splitter and metadata extractor" "$M3" "m3,parsing" \
"## Why

After layout detection identifies question blocks and OCR extracts text, the parser must combine these to produce structured question objects. Each question needs: the question text, its number, marks allocation, sub-parts (a, b, c), and question type.

This is harder than it sounds. Some papers number questions as \"1.\", others as \"Q.1\", others as \"1)\". Marks might be in brackets \"[5]\", parentheses \"(5 marks)\", or in a separate column. Sub-parts might be \"(a)\", \"(i)\", or just indented. The parser must handle all these variations.

## What needs to be built

Question splitter using layout detection + text parsing, metadata extraction for marks/number/type/sub-parts.

## Files to create or update

- \`src/parsing/question_splitter.py\` - Split pages into individual questions
- \`src/parsing/metadata_extractor.py\` - Extract marks, number, type, sub-parts
- \`src/parsing/question_parser.py\` - Orchestrate splitting + metadata extraction

## How this affects overall development

The question bank (#15) stores these parsed questions. Topic tagging (#14) operates on parsed question text. Answer generation (#17) needs to know the question type to select the right solution strategy. Every downstream module depends on correct parsing.

## How to test locally

\`\`\`bash
python -m src.parsing.question_parser --input data/sample_papers/gate_cs_2024_page1.png

python -c \"
from src.parsing.question_parser import parse_page
questions = parse_page('data/sample_papers/gate_cs_2024_page1.png')
for q in questions:
    print(f'Q{q.number} [{q.marks} marks] ({q.type}): {q.text[:80]}...')
    if q.sub_parts:
        for sp in q.sub_parts:
            print(f'  ({sp.label}) {sp.text[:60]}...')
\"

pytest tests/test_question_parser.py -v
\`\`\`

## Acceptance Criteria

- [ ] Correctly splits a full page into individual questions
- [ ] Extracts question number (handles \"1.\", \"Q.1\", \"1)\", \"Question 1\")
- [ ] Extracts marks (handles \"[5]\", \"(5 marks)\", \"5M\", marks column)
- [ ] Detects sub-parts (a/b/c, i/ii/iii, indented blocks)
- [ ] Determines question type based on content (MCQ if options present, numerical if \"answer is ___\")
- [ ] Handles partial questions spanning page breaks (flags for manual review)
- [ ] At least 5 tests: simple numbered, marks extraction, sub-parts, MCQ detection, page break

## Branch

\`feature/issue-10-question-parser\`

## Depends on

Closes #9"

create_issue 11 "Handle multi-format papers (MCQ, subjective, numerical, mixed)" "$M3" "m3,parsing" \
"## Why

Different exams use different formats. JEE Mains is entirely MCQ (4 options per question). GATE mixes MCQ with numerical answer type (NAT). University exams are primarily subjective (long-answer). Some papers mix all types in different sections.

The parser must detect the format and apply type-specific parsing rules. MCQ parsing needs to identify options (A/B/C/D). Numerical parsing needs to identify the answer format. Subjective parsing needs to handle multi-paragraph questions.

## What needs to be built

Format detection and type-specific parsing logic for MCQ, subjective, numerical, and mixed papers.

## Files to create or update

- \`src/parsing/question_parser.py\` - Extend with format-specific parsers

## How this affects overall development

Question type affects answer generation (#17) - MCQ solutions explain why each option is right/wrong, numerical solutions show computation, subjective solutions are structured essays. Mock generation (#24) needs to match the exam's format distribution.

## How to test locally

\`\`\`bash
python -m src.parsing.question_parser --input data/sample_papers/jee_mains_mcq.png
python -m src.parsing.question_parser --input data/sample_papers/gate_mixed.png

python -c \"
from src.parsing.question_parser import parse_page
questions = parse_page('data/sample_papers/jee_mains_mcq.png')
for q in questions:
    print(f'Q{q.number} ({q.type}): {q.text[:60]}')
    if q.options:
        for opt in q.options:
            print(f'  {opt.label}) {opt.text}')
\"
\`\`\`

## Acceptance Criteria

- [ ] Detects paper format: MCQ, subjective, numerical, mixed
- [ ] MCQ parser extracts options (A/B/C/D) with text
- [ ] Numerical parser identifies answer type (integer, decimal, range)
- [ ] Subjective parser handles multi-paragraph questions
- [ ] Mixed papers: correctly classifies each question independently
- [ ] At least 4 tests: pure MCQ, pure subjective, numerical, mixed paper

## Branch

\`feature/issue-11-multi-format\`

## Depends on

Closes #10"

create_issue 12 "Build OCR confidence scorer and manual correction interface" "$M3" "m3,cv,frontend" \
"## Why

OCR is never 100% accurate, especially on phone photos and old scans. Rather than silently propagating errors into topic tagging and answer generation, the system should flag low-confidence text and let users correct it before processing continues.

The correction interface shows the original image alongside the extracted text, highlighting words with low confidence in yellow/red. Users click a word, see the original image region, and type the correction. This crowdsourced correction also improves future OCR accuracy.

## What needs to be built

Confidence scoring per text block and a frontend correction interface.

## Files to create or update

- \`src/cv/confidence_scorer.py\` - Aggregate OCR confidence per block
- \`frontend/src/components/CorrectionUI.jsx\` - Side-by-side correction interface

## How this affects overall development

Corrected text flows into all downstream modules. Without correction, a misread \"O(n log n)\" as \"O(n lag n)\" propagates through topic tagging, answer generation, and the question bank.

## How to test locally

\`\`\`bash
uvicorn src.api.main:app --reload
cd frontend && npm run dev

# Navigate to /papers/1/correct
# Low confidence words highlighted in yellow/red
# Click a word to correct it

curl http://localhost:8000/api/papers/1/ocr-review
\`\`\`

## Acceptance Criteria

- [ ] Confidence score (0-1) per text block based on OCR engine output
- [ ] Blocks with confidence < 0.7 highlighted in yellow, < 0.5 in red
- [ ] Side-by-side view: original image region + extracted text
- [ ] Click-to-correct: click a word, type correction, save
- [ ] Corrections stored in database and applied to question text
- [ ] Contributor earns points for corrections
- [ ] At least 3 tests: confidence scoring, correction save, correction application

## Branch

\`feature/issue-12-correction-ui\`

## Depends on

Closes #6, Closes #10"

# ─── M4 Issues (#13-16) ───────────────────────────────────────────────────

create_issue 13 "Build syllabus ingestion system" "$M4" "m4,agent" \
"## Why

Topic tagging needs a reference. Without a syllabus, the LLM has to guess what topics exist for a course, leading to inconsistent and overlapping tags. With a syllabus, the LLM maps each question to a specific topic in a known hierarchy.

Indian university syllabi are typically structured as: Unit > Topic > Subtopic. For competitive exams (JEE, GATE), the official syllabus is published by NTA/GATE committee. The system can also accept manually created topic lists.

## What needs to be built

Syllabus upload and parsing system that extracts a hierarchical topic tree.

## Files to create or update

- \`src/agents/syllabus_parser.py\` - LLM-assisted syllabus parsing
- \`src/api/routes/syllabus.py\` - Syllabus upload and retrieval endpoints

## How this affects overall development

The topic tagger (#14) maps questions to this syllabus. The frequency analyzer (#21) counts by syllabus topics. The prediction agent (#22) predicts based on syllabus topic list. The study planner (#26) organizes by syllabus. Without consistent topic structure, all analytics are unreliable.

## How to test locally

\`\`\`bash
curl -X POST http://localhost:8000/api/syllabus/upload \\
  -F \"file=@data/syllabus/gate_cs_2026.pdf\" \\
  -F \"exam_id=1\"

curl http://localhost:8000/api/syllabus/1/topics

pytest tests/test_syllabus_parser.py -v
\`\`\`

## Acceptance Criteria

- [ ] Accepts syllabus as PDF or plain text
- [ ] Extracts hierarchical topic tree (unit > topic > subtopic)
- [ ] LLM assists in structuring unstructured syllabi
- [ ] Supports manual topic entry/editing via API
- [ ] Topic tree linked to specific exam/course
- [ ] At least 3 tests: PDF syllabus, text syllabus, manual topic creation

## Branch

\`feature/issue-13-syllabus\`

## Depends on

Closes #2"

create_issue 14 "Build LLM-based topic tagger agent" "$M4" "m4,agent" \
"## Why

Manually tagging thousands of questions to syllabus topics is impractical. The topic tagger agent uses the LLM to read each question's text and map it to the most relevant syllabus topic(s).

This is a LangGraph agent because it may need multi-step reasoning: first classify the broad subject area, then narrow down to the specific topic, then handle edge cases (question spans two topics, question not in the syllabus).

## What needs to be built

LangGraph topic tagger agent with syllabus-aware prompting.

## Files to create or update

- \`src/agents/topic_tagger.py\` - Topic tagger agent

## How this affects overall development

Topic tags are the foundation of all analytics. Frequency analysis (#21) counts by topic. Predictions (#22) rank topics. The question bank (#15) filters by topic. The study planner (#26) organizes by topic. If tagging is inaccurate, every analysis is wrong.

## How to test locally

\`\`\`bash
python -m src.agents.topic_tagger --paper-id 1

python -c \"
from src.agents.topic_tagger import TopicTaggerAgent
agent = TopicTaggerAgent()
result = agent.tag(
    question_text='What is the time complexity of inserting into an AVL tree?',
    syllabus_id=1
)
print(f'Topic: {result.topic_path}')
print(f'Confidence: {result.confidence:.2f}')
\"

pytest tests/test_topic_tagger.py -v
\`\`\`

## Acceptance Criteria

- [ ] Maps questions to syllabus topics with > 85% accuracy (verified on 50+ manual tags)
- [ ] Returns topic path (e.g., \"Data Structures > Trees > AVL Trees\")
- [ ] Handles multi-topic questions (returns ranked list)
- [ ] Uses syllabus as reference (not free-form tagging)
- [ ] Confidence score per tag
- [ ] Batch processing: tag all questions in a paper in one call
- [ ] At least 4 tests: single topic, multi-topic, unknown topic, batch tagging

## Branch

\`feature/issue-14-topic-tagger\`

## Depends on

Closes #10, Closes #13"

create_issue 15 "Build searchable question bank with full-text search" "$M4" "m4,frontend" \
"## Why

The question bank is the core product that students interact with daily. They need to find questions by topic, year, type, marks, or keyword.

PostgreSQL's built-in full-text search (tsvector/tsquery) is used rather than an external search engine because it requires no additional infrastructure, handles stemming and ranking natively, and integrates directly with SQLAlchemy.

## What needs to be built

Full-text search API with combined filters, and a frontend question bank interface.

## Files to create or update

- \`src/api/routes/questions.py\` - Search and filter endpoints
- \`frontend/src/components/QuestionBank.jsx\` - Question bank UI
- \`frontend/src/components/QuestionCard.jsx\` - Individual question display

## How this affects overall development

The question bank is displayed in the dashboard (#29). Students use it to browse, search, and study questions. The mock generator (#24) pulls questions from the bank. The frequency analyzer (#21) queries the bank for topic counts.

## How to test locally

\`\`\`bash
curl \"http://localhost:8000/api/questions?q=binary+tree&exam_type=gate\"
curl \"http://localhost:8000/api/questions?topic=Data+Structures&year=2024&type=mcq\"

cd frontend && npm run dev
# Navigate to /questions
\`\`\`

## Acceptance Criteria

- [ ] Full-text search on question text using PostgreSQL tsvector
- [ ] Filter by: topic, year, exam type, question type, marks range
- [ ] Filters combine (AND logic): topic=Trees AND year=2024 AND type=MCQ
- [ ] Paginated results (20 per page default)
- [ ] Search results ranked by relevance
- [ ] Frontend: search bar + filter dropdowns + question cards
- [ ] At least 4 tests: keyword search, filter combination, pagination, empty results

## Branch

\`feature/issue-15-question-bank\`

## Depends on

Closes #14"

create_issue 16 "Implement question deduplication" "$M4" "m4,agent" \
"## Why

The same question often appears across multiple years, sometimes verbatim, sometimes paraphrased. Without deduplication, the frequency analyzer counts this topic twice, inflating its importance score.

LLM-based similarity detection is used because paraphrased questions cannot be caught by exact text matching or even cosine similarity on embeddings.

## What needs to be built

Deduplication pipeline that detects same/paraphrased questions and groups them.

## Files to create or update

- \`src/parsing/deduplicator.py\` - LLM-based deduplication

## How this affects overall development

Clean frequency data depends on deduplication. If duplicates are not detected, the frequency analyzer (#21) and prediction agent (#22) produce skewed results. The question bank (#15) can also show \"appeared in 2020, 2022, 2024\" for deduplicated questions.

## How to test locally

\`\`\`bash
python -c \"
from src.parsing.deduplicator import find_duplicates
questions = [
    'Find the time complexity of inserting into an AVL tree.',
    'What is the time complexity for insertion in an AVL tree?',
    'Explain the process of BFS traversal in a graph.',
]
groups = find_duplicates(questions)
print(f'Groups: {len(groups)}')
for g in groups:
    print(f'  Canonical: {g.canonical}')
    print(f'  Duplicates: {g.duplicates}')
\"

pytest tests/test_deduplicator.py -v
\`\`\`

## Acceptance Criteria

- [ ] Detects exact duplicate questions
- [ ] Detects paraphrased questions asking the same thing
- [ ] Groups duplicates with a canonical (best-worded) question
- [ ] Records which years/papers each variant appeared in
- [ ] Does not falsely group questions on the same topic but asking different things
- [ ] Batch processing: deduplicate all questions in a course
- [ ] At least 4 tests: exact duplicate, paraphrase, different questions on same topic, batch

## Branch

\`feature/issue-16-deduplication\`

## Depends on

Closes #14"

# ─── M5 Issues (#17-20) ───────────────────────────────────────────────────

create_issue 17 "Build answer generator agent" "$M5" "m5,agent" \
"## Why

This is the killer feature. Students do not just want \"the answer is B.\" They want to know why B is correct, why A/C/D are wrong, and how to solve the problem step by step. For numerical questions, they want the full derivation. For subjective questions, they want a structured answer they could write in an exam.

The agent adapts its output based on question type. MCQ: explain each option. Numerical: show computation steps. Subjective: structured essay. Proof: formal proof with lemmas.

Groq is the default LLM because its free tier provides fast inference (< 3 seconds per question).

## What needs to be built

LangGraph answer generation agent with type-specific solution strategies.

## Files to create or update

- \`src/agents/answer_generator.py\` - Answer generator agent

## How this affects overall development

Solutions are displayed in the answer UI (#20), stored in the database, used by the quality scorer (#19), and verified by the verifier (#18). This is the primary value proposition of ExamLens.

## How to test locally

\`\`\`bash
python -m src.agents.answer_generator --question-id 1

python -c \"
from src.agents.answer_generator import AnswerGeneratorAgent
agent = AnswerGeneratorAgent()

solution = agent.generate(
    question='Which data structure uses LIFO? (A) Queue (B) Stack (C) Array (D) Graph',
    question_type='mcq'
)
print(f'Answer: {solution.answer}')
print(f'Steps: {len(solution.steps)}')
for step in solution.steps:
    print(f'  - {step}')
\"

pytest tests/test_answer_generator.py -v
\`\`\`

## Acceptance Criteria

- [ ] Generates step-by-step solutions for MCQ, numerical, and subjective questions
- [ ] MCQ solutions explain why the correct option is right AND why others are wrong
- [ ] Numerical solutions show full computation with intermediate steps
- [ ] Subjective solutions are structured (intro, body, conclusion)
- [ ] Includes LaTeX for math content
- [ ] Uses Groq (free tier) by default, configurable
- [ ] Generates in < 5 seconds per question
- [ ] At least 5 tests: MCQ, numerical, subjective, math-heavy, edge case (ambiguous question)

## Branch

\`feature/issue-17-answer-generator\`

## Depends on

Closes #14"

create_issue 18 "Implement answer verifier agent" "$M5" "m5,agent" \
"## Why

LLMs hallucinate. A generated answer might have the right reasoning but wrong final answer, or correct answer but flawed logic. The verifier is a separate agent that cross-checks generated answers against official answer keys (when available) and flags discrepancies.

Separation from the generator is deliberate: the generator optimizes for explanation quality, the verifier optimizes for correctness. Different failure modes, different prompts.

## What needs to be built

Answer verification agent with official key matching and independent verification.

## Files to create or update

- \`src/agents/answer_verifier.py\` - Verification agent

## How this affects overall development

The quality scorer (#19) uses verification results to assign confidence levels. Verified answers get \"high\" confidence, unverified but consistent get \"medium\", flagged discrepancies get \"low.\"

## How to test locally

\`\`\`bash
python -c \"
from src.agents.answer_verifier import AnswerVerifierAgent
verifier = AnswerVerifierAgent()

result = verifier.verify(
    question_id=1,
    generated_answer='B',
    official_answer='B'
)
print(f'Match: {result.matches_key}')
print(f'Confidence: {result.confidence}')

result = verifier.verify(
    question_id=2,
    generated_answer='42',
    official_answer=None
)
print(f'Independent check: {result.independent_answer}')
print(f'Consistent: {result.consistent}')
\"

pytest tests/test_answer_verifier.py -v
\`\`\`

## Acceptance Criteria

- [ ] Matches generated answer against official key when available
- [ ] Runs independent verification (second LLM call) when no key available
- [ ] Reports: matches_key (bool), independent_answer, consistent (bool), explanation
- [ ] Handles MCQ (letter matching), numerical (tolerance range), subjective (semantic comparison)
- [ ] Flags discrepancies clearly with explanation of the mismatch
- [ ] At least 4 tests: key match, key mismatch, independent verify consistent, independent verify inconsistent

## Branch

\`feature/issue-18-answer-verifier\`

## Depends on

Closes #17"

create_issue 19 "Add solution quality scorer and confidence rating" "$M5" "m5,agent" \
"## Why

Students need to know how much to trust each solution. A solution verified against an official answer key is highly reliable. A solution generated by the LLM but independently verified is moderately reliable. A solution where the generator and verifier disagree needs manual review.

The three-tier system (high/medium/low) is simple enough that students understand it immediately: green checkmark = trust it, yellow = probably right, red = verify yourself.

## What needs to be built

Quality scoring based on verification results, completeness, and step coherence.

## Files to create or update

- \`src/agents/quality_scorer.py\` - Solution quality scorer

## How this affects overall development

Confidence ratings appear in the answer display (#20) and the question bank (#15). Low-confidence solutions are flagged for community correction.

## How to test locally

\`\`\`bash
python -c \"
from src.agents.quality_scorer import score_solution

score = score_solution(verified_against_key=True, key_matches=True, steps_complete=True)
print(f'Verified + match: {score.confidence}')

score = score_solution(verified_against_key=False, independent_consistent=True, steps_complete=True)
print(f'Independent consistent: {score.confidence}')

score = score_solution(verified_against_key=False, independent_consistent=False, steps_complete=False)
print(f'Inconsistent: {score.confidence}')
\"

pytest tests/test_quality_scorer.py -v
\`\`\`

## Acceptance Criteria

- [ ] Three confidence levels: high, medium, low
- [ ] High: verified against official key and matches
- [ ] Medium: no key available but independent verification consistent
- [ ] Low: verification inconsistent or steps incomplete
- [ ] Factors in: key verification, independent check, step completeness, LaTeX validity
- [ ] At least 3 tests: high confidence, medium confidence, low confidence

## Branch

\`feature/issue-19-quality-scorer\`

## Depends on

Closes #18"

create_issue 20 "Build answer display UI with LaTeX rendering" "$M5" "m5,frontend" \
"## Why

A solution with proper math rendering, collapsible steps, and a confidence badge is infinitely more useful than a wall of plain text. Students studying JEE Math need to see integrals, fractions, and matrices rendered correctly.

KaTeX is chosen over MathJax for rendering because it is significantly faster (renders in < 1ms vs MathJax's 100ms+ per equation).

## What needs to be built

React component for solution display with LaTeX rendering, collapsible steps, and confidence indicator.

## Files to create or update

- \`frontend/src/components/SolutionDisplay.jsx\` - Solution display component
- \`frontend/src/components/LaTeXRenderer.jsx\` - KaTeX wrapper component

## How this affects overall development

This is the primary interface for viewing solutions. The question bank (#15) links to this. Mock test grading (#25) uses it. The dashboard (#29) embeds it.

## How to test locally

\`\`\`bash
cd frontend && npm install && npm run dev
# Navigate to /questions/1/solution
# Should show: confidence badge, collapsible steps, LaTeX equations, report button
\`\`\`

## Acceptance Criteria

- [ ] KaTeX renders LaTeX equations correctly (fractions, integrals, matrices, Greek)
- [ ] Steps are collapsible (click to reveal each step)
- [ ] Confidence badge: green (high), yellow (medium), red (low)
- [ ] MCQ solutions show why each option is correct/incorrect
- [ ] \"Report incorrect\" button for community correction
- [ ] Mobile-friendly (readable on 375px screens)
- [ ] At least 3 tests: LaTeX rendering, step collapse/expand, confidence badge display

## Branch

\`feature/issue-20-answer-display\`

## Depends on

Closes #17"

# ─── M6 Issues (#21-23) ───────────────────────────────────────────────────

create_issue 21 "Build topic frequency analyzer with trend detection" "$M6" "m6,analytics" \
"## Why

\"What comes every year?\" is the single most common question students ask when preparing for exams. The frequency analyzer answers this with data: a topic-year matrix showing exactly how many questions appeared per topic per year, plus trend classification (rising, falling, stable, cyclic).

Trend detection uses simple statistical methods: linear regression slope for rising/falling, standard deviation for stable, and autocorrelation for cyclic patterns.

## What needs to be built

Topic-year matrix computation and trend classification.

## Files to create or update

- \`src/analysis/frequency_analyzer.py\` - Frequency matrix and statistics
- \`src/analysis/trend_detector.py\` - Trend classification algorithms

## How this affects overall development

The prediction agent (#22) uses frequency and trends as primary inputs. The heatmap (#23) visualizes this data. The study planner (#26) prioritizes high-frequency topics. This is the analytical foundation of ExamLens.

## How to test locally

\`\`\`bash
python -c \"
from src.analysis.frequency_analyzer import FrequencyAnalyzer
analyzer = FrequencyAnalyzer()
matrix = analyzer.build_matrix(exam_id=1)
for topic, years in matrix.items():
    total = sum(years.values())
    trend = analyzer.detect_trend(years)
    print(f'{topic}: {years} | total={total} | trend={trend}')
\"

pytest tests/test_frequency_analyzer.py -v
\`\`\`

## Acceptance Criteria

- [ ] Builds topic-year matrix from tagged questions
- [ ] Handles deduplicated questions (counts once, not per variant)
- [ ] Trend classification: rising, falling, stable, cyclic, insufficient_data
- [ ] Rising: positive slope over 3+ years
- [ ] Cyclic: topic appears with regular periodicity (every 2-3 years)
- [ ] Handles missing years (not all topics appear every year)
- [ ] At least 4 tests: stable topic, rising topic, cyclic topic, sparse data

## Branch

\`feature/issue-21-frequency-analyzer\`

## Depends on

Closes #14"

create_issue 22 "Build exam prediction agent" "$M6" "m6,agent" \
"## Why

Frequency data tells you what happened. Prediction tells you what will happen. The prediction agent combines frequency, trends, recency, and gap analysis to rank topics by probability of appearing in the next exam.

Gap analysis is particularly valuable: if a topic that normally appears every year was absent for the last 2 years, its probability increases.

## What needs to be built

LangGraph prediction agent combining multiple scoring factors.

## Files to create or update

- \`src/agents/prediction_agent.py\` - Prediction agent
- \`src/analysis/importance_scorer.py\` - Multi-factor scoring

## How this affects overall development

Predictions appear in the dashboard (#29) as \"Top topics to study.\" The study planner (#26) uses predictions to prioritize. This is a differentiating feature.

## How to test locally

\`\`\`bash
python -m src.agents.prediction_agent --exam-id 1

python -c \"
from src.agents.prediction_agent import PredictionAgent
agent = PredictionAgent()
predictions = agent.predict(exam_id=1, target_year=2027)
print('Top 10 predicted topics for GATE CS 2027:')
for i, p in enumerate(predictions[:10], 1):
    print(f'{i}. {p.topic} (score: {p.score:.2f}, reason: {p.reason})')
\"

pytest tests/test_prediction_agent.py -v
\`\`\`

## Acceptance Criteria

- [ ] Ranks topics by predicted probability of appearing
- [ ] Scoring factors: frequency, trend, recency, gap, marks weight
- [ ] Each prediction includes explanation (why this topic ranks high)
- [ ] Gap detection: absent topic with high historical frequency gets boosted
- [ ] Handles exams with < 3 years of data (uses only frequency, no trend)
- [ ] At least 4 tests: high-frequency topic, gap detection, rising trend, insufficient data

## Branch

\`feature/issue-22-prediction-agent\`

## Depends on

Closes #21"

create_issue 23 "Create analytics visualization" "$M6" "m6,analytics,frontend" \
"## Why

Numbers in a table are hard to interpret. A heatmap where dark cells scream \"this topic appears every year\" communicates the same information in a glance. Trend line charts show at-a-glance whether a topic is rising or falling. These visualizations make the analytics actionable.

Export capability (CSV/JSON) is included because some students want to analyze the data in Excel or share it with their study group.

## What needs to be built

Topic frequency heatmap, trend charts, marks distribution, and export functionality.

## Files to create or update

- \`frontend/src/components/TopicHeatmap.jsx\` - Interactive heatmap
- \`frontend/src/components/TrendChart.jsx\` - Trend line charts
- \`src/api/routes/analytics.py\` - Analytics data endpoints with export

## How this affects overall development

Visualizations are displayed in the dashboard (#29). This is the \"wow factor\" feature.

## How to test locally

\`\`\`bash
cd frontend && npm run dev
# Navigate to /analytics?exam_id=1

curl \"http://localhost:8000/api/analytics/export?exam_id=1&format=csv\" > analysis.csv
curl \"http://localhost:8000/api/analytics/export?exam_id=1&format=json\" > analysis.json
\`\`\`

## Acceptance Criteria

- [ ] Heatmap: topics as rows, years as columns, color intensity = question count
- [ ] Heatmap is interactive: hover shows details, click filters question bank
- [ ] Trend chart: line chart per topic showing frequency over years
- [ ] Marks distribution: bar chart showing marks allocation across topics
- [ ] Export as CSV and JSON with all analytics data
- [ ] Responsive: usable on tablet (768px) and laptop (1024px+)
- [ ] At least 3 tests: heatmap data endpoint, trend data endpoint, export format

## Branch

\`feature/issue-23-analytics-viz\`

## Depends on

Closes #21"

# ─── M7 Issues (#24-27) ───────────────────────────────────────────────────

create_issue 24 "Build mock paper generator agent" "$M7" "m7,agent" \
"## Why

Random question sets are not mock exams. A real GATE CS paper has: 65 questions, 100 marks, 10 questions from each major topic, difficulty mix of easy/medium/hard, specific marks distribution (1-mark and 2-mark questions). The mock generator must match this pattern exactly for realistic practice.

The agent analyzes real papers to learn the pattern (marks distribution, topic coverage, question type ratios, difficulty distribution) and generates mocks that match.

## What needs to be built

LangGraph mock generation agent with pattern matching to real exam structure.

## Files to create or update

- \`src/agents/mock_generator.py\` - Mock generator agent
- \`src/mock/paper_generator.py\` - Paper assembly logic

## How this affects overall development

Mock tests are the primary practice tool. The test interface (#25) displays generated mocks. The study planner (#26) uses mock results to identify weak areas. The progress tracker (#27) tracks mock scores.

## How to test locally

\`\`\`bash
python -m src.agents.mock_generator --exam-id 1 --output mock_gate_cs.json

python -c \"
from src.agents.mock_generator import MockGeneratorAgent
from collections import Counter
agent = MockGeneratorAgent()
mock = agent.generate(exam_id=1)
print(f'Questions: {len(mock.questions)}')
print(f'Total marks: {mock.total_marks}')
print(f'Topics covered: {len(set(q.topic for q in mock.questions))}')
print(f'Types: {dict(Counter(q.type for q in mock.questions))}')
\"

pytest tests/test_mock_generator.py -v
\`\`\`

## Acceptance Criteria

- [ ] Generated mock matches real exam pattern: question count, total marks, marks distribution
- [ ] Topic coverage proportional to real exam (no topic overrepresented)
- [ ] Mix of question types matching the exam format (MCQ/numerical/subjective ratios)
- [ ] No duplicate questions from the same year (fresh combinations)
- [ ] Difficulty estimate per question (easy/medium/hard based on historical data)
- [ ] Generates in < 10 seconds
- [ ] At least 4 tests: GATE mock pattern, JEE mock pattern, marks distribution, topic coverage

## Branch

\`feature/issue-24-mock-generator\`

## Depends on

Closes #21"

create_issue 25 "Build mock test taking interface with auto-grading" "$M7" "m7,frontend" \
"## Why

Students need to practice under exam conditions. A timer creates urgency. Question navigation lets students skip and return. Auto-save prevents lost work. Instant MCQ grading provides immediate feedback.

The interface must feel like a real CBT (Computer Based Test) because JEE/GATE are conducted as CBTs. Familiarity reduces test anxiety.

## What needs to be built

Mock test taking interface with timer, navigation, auto-save, and auto-grading.

## Files to create or update

- \`frontend/src/pages/MockTest.jsx\` - Test taking page
- \`src/api/routes/mock.py\` - Mock test API (create, submit, grade)
- \`src/mock/grader.py\` - Auto-grading logic

## How this affects overall development

Mock results feed into the study planner (#26) and progress tracker (#27). The solution display (#20) shows correct answers after submission.

## How to test locally

\`\`\`bash
cd frontend && npm run dev
# Navigate to /mock/new?exam_id=1
# Should show: question paper, timer, question palette, navigation buttons
# Take the mock, submit, see instant results
\`\`\`

## Acceptance Criteria

- [ ] Timer counts down from exam duration (3 hours for GATE, etc.)
- [ ] Question palette: numbered buttons showing answered/unanswered/marked-for-review
- [ ] Navigation: next/previous, jump to question number, mark for review
- [ ] Auto-save every 30 seconds (resume on disconnect)
- [ ] MCQ grading instant on submit (correct/incorrect/unattempted)
- [ ] Results page: score, percentage, per-question review with solutions
- [ ] At least 4 tests: timer, auto-save, MCQ grading, results calculation

## Branch

\`feature/issue-25-mock-interface\`

## Depends on

Closes #24"

create_issue 26 "Build personalized study plan agent" "$M7" "m7,agent" \
"## Why

A ranked topic list is not a study plan. Students need: \"Day 1: Study Binary Trees (2 hours) - focus on AVL rotations (your weakest subtopic). Practice 5 questions from the question bank.\"

The study plan agent considers: exam date (how many days left), topic importance (from prediction), student weakness (from mock results), and available study time per day.

## What needs to be built

LangGraph study plan agent with personalization based on mock results and exam predictions.

## Files to create or update

- \`src/agents/study_planner.py\` - Study plan agent
- \`src/api/routes/study.py\` - Study plan endpoints

## How this affects overall development

The study plan is displayed in the dashboard (#29) and updated after each mock test. The progress tracker (#27) shows plan completion.

## How to test locally

\`\`\`bash
python -c \"
from src.agents.study_planner import StudyPlannerAgent
agent = StudyPlannerAgent()
plan = agent.generate(
    user_id=1,
    exam_id=1,
    exam_date='2027-02-15',
    hours_per_day=4,
    weak_topics=['Dynamic Programming', 'Graph Algorithms']
)
for day in plan.days[:5]:
    print(f'Day {day.number} ({day.date}):')
    for task in day.tasks:
        print(f'  - {task.topic} ({task.hours}h): {task.description}')
\"

pytest tests/test_study_planner.py -v
\`\`\`

## Acceptance Criteria

- [ ] Generates daily study plan with specific topics and time allocations
- [ ] Prioritizes: high-importance topics (from prediction) + weak topics (from mocks)
- [ ] Respects available hours per day
- [ ] Includes practice question links from the question bank
- [ ] Updates after each mock test (re-prioritizes based on new results)
- [ ] Handles varying prep durations (30 days vs 90 days)
- [ ] At least 3 tests: short plan, long plan, plan update after mock

## Branch

\`feature/issue-26-study-planner\`

## Depends on

Closes #22, Closes #25"

create_issue 27 "Add progress tracker" "$M7" "m7,frontend" \
"## Why

Students need visible evidence that their preparation is working. A chart showing mock scores climbing from 45% to 72% over 4 weeks is motivating. A topic coverage meter showing \"68% of syllabus studied\" creates accountability.

The progress tracker also identifies persistent weak areas across multiple mocks.

## What needs to be built

Progress tracking across mock tests with score trends and weak area identification.

## Files to create or update

- \`src/mock/progress_tracker.py\` - Progress tracking logic
- \`frontend/src/components/ProgressDashboard.jsx\` - Progress visualization

## How this affects overall development

Progress data appears in the dashboard (#29). The study planner (#26) uses progress data to update plans.

## How to test locally

\`\`\`bash
cd frontend && npm run dev
# Navigate to /progress

python -c \"
from src.mock.progress_tracker import ProgressTracker
tracker = ProgressTracker(user_id=1)
summary = tracker.get_summary()
print(f'Mocks taken: {summary.total_mocks}')
print(f'Average score: {summary.avg_score:.1f}%')
print(f'Trend: {summary.trend}')
print(f'Weak topics: {summary.weak_topics}')
print(f'Topics covered: {summary.coverage_pct:.0f}%')
\"

pytest tests/test_progress_tracker.py -v
\`\`\`

## Acceptance Criteria

- [ ] Score trend chart across mock tests (Recharts line chart)
- [ ] Topic coverage meter (percentage of syllabus studied)
- [ ] Weak area identification (topics consistently below average)
- [ ] Study streak counter (consecutive days of activity)
- [ ] Per-topic score breakdown across mocks
- [ ] At least 3 tests: score tracking, weak topic detection, coverage calculation

## Branch

\`feature/issue-27-progress-tracker\`

## Depends on

Closes #25"

# ─── M8 Issues (#28-30) ───────────────────────────────────────────────────

create_issue 28 "Build PYQ scraper agent" "$M8" "m8,scraper,agent" \
"## Why

Students should not have to hunt for papers and upload them manually. The scraper agent crawls university websites and exam portals, finds PYQ PDFs, downloads them, and feeds them into the ingestion pipeline automatically.

Playwright is used instead of requests+BeautifulSoup because many university sites are JavaScript-rendered (React/Angular SPAs, CAPTCHA-gated downloads).

## What needs to be built

Playwright-based scraper agent targeting university sites and exam portals.

## Files to create or update

- \`src/agents/scraper_agent.py\` - Scraper agent with site-specific parsers

## How this affects overall development

The scraper populates the paper library automatically, making ExamLens useful from day one.

## How to test locally

\`\`\`bash
python -m src.agents.scraper_agent --source gate --years 2024,2025

python -c \"
from src.agents.scraper_agent import ScraperAgent
agent = ScraperAgent()
papers = agent.scrape(source='gate', subject='cs', years=[2024, 2025])
print(f'Papers found: {len(papers)}')
for p in papers:
    print(f'  {p.name}: {p.url}')
\"

pytest tests/test_scraper_agent.py -v
\`\`\`

## Acceptance Criteria

- [ ] Fetches papers from at least 3 sources (GATE official, AKTU, one more)
- [ ] Respects robots.txt and rate limits (configurable delay between requests)
- [ ] Handles JS-rendered sites via Playwright
- [ ] Downloads PDFs and feeds into ingestion pipeline
- [ ] Logs all fetched URLs and success/failure
- [ ] Handles site changes gracefully (clear error, not crash)
- [ ] At least 3 tests: successful scrape, rate limiting, error handling

## Branch

\`feature/issue-28-scraper\`

## Depends on

Closes #3"

create_issue 29 "Build student dashboard with mobile-responsive PWA" "$M8" "m8,frontend" \
"## Why

The dashboard is where everything comes together. Question bank, analytics, mock tests, study plan, and progress - all in one place. On mobile, students check their study plan on the bus, take a quick practice during lunch, or review their weak areas before bed.

PWA (Progressive Web App) lets students \"install\" ExamLens on their phone's home screen without an app store.

## What needs to be built

React dashboard with all features accessible, mobile-responsive, PWA enabled.

## Files to create or update

- \`frontend/src/pages/Dashboard.jsx\` - Main dashboard
- \`frontend/public/manifest.json\` - PWA manifest
- \`frontend/public/service-worker.js\` - Offline caching
- \`frontend/public/icons/\` - App icons

## How this affects overall development

This is the final integration of all M1-M7 work.

## How to test locally

\`\`\`bash
cd frontend && npm install && npm run dev
# Desktop: sidebar navigation, all sections visible
# Mobile (375px): hamburger menu, touch-friendly

npm run build && npx serve dist/
# On Android Chrome: \"Add to Home Screen\" should appear
\`\`\`

## Acceptance Criteria

- [ ] Dashboard sections: Question Bank, Analytics, Mock Tests, Study Plan, Progress
- [ ] Navigation: sidebar on desktop, hamburger menu on mobile
- [ ] All interactive elements have 44px minimum touch targets
- [ ] No horizontal scroll on 375px screens
- [ ] PWA manifest with icons, theme color, start URL
- [ ] Service worker caches static assets
- [ ] Lighthouse PWA audit > 80
- [ ] At least 3 tests: navigation, responsive layout, data loading

## Branch

\`feature/issue-29-dashboard\`

## Depends on

Closes #15, Closes #20, Closes #23, Closes #25, Closes #27"

create_issue 30 "E2E testing, deployment, demo video" "$M8" "m8,infra" \
"## Why

A project that only runs on your laptop is a demo, not a product. E2E testing proves the full pipeline works end-to-end: upload paper -> OCR -> parse questions -> tag topics -> generate answers -> display. Deployment means anyone with a URL can use ExamLens. The demo video is the portfolio artifact for LinkedIn.

## What needs to be built

E2E tests, Docker deployment to Railway/Render, demo video script.

## Files to create or update

- \`tests/test_e2e.py\` - End-to-end test suite
- \`docs/deployment_guide.md\` - Deployment steps and live URL
- \`docs/architecture.md\` - System architecture diagram
- \`docs/demo_script.md\` - Demo video talking points

## How this affects overall development

This is the capstone. Every issue from 1 to 29 assembles here.

## How to test locally

\`\`\`bash
pytest tests/test_e2e.py -v

docker-compose up --build
curl http://localhost:8000/health
open http://localhost:5173

npm install -g @railway/cli
railway login && railway init && railway up
curl https://your-app.up.railway.app/health
\`\`\`

## Acceptance Criteria

- [ ] E2E test processes 5 sample papers through full pipeline without errors
- [ ] \`docker-compose up --build\` starts all services
- [ ] Deployed to Railway/Render with live public URL
- [ ] Frontend loads on live URL
- [ ] \`docs/deployment_guide.md\`: live URL, redeploy steps, env vars
- [ ] \`docs/architecture.md\`: system diagram, tech stack, data flow
- [ ] Demo video (3-5 min): upload paper, see OCR, browse question bank, view solutions, take mock, see analytics
- [ ] All existing tests pass

## Branch

\`feature/issue-30-deployment\`

## Depends on

Closes #29"

echo ""
echo "========================================="
echo "All 30 issues created for $REPO!"
echo "========================================="
