# Pod Guide

Pod structure, collaboration model, sprint timeline, and Q&A rules for ExamLens AI.

---

## Pod Members

| Role | Name | GitHub Username | Responsibility |
|------|------|----------------|---------------|
| Faculty (Product Manager) | TBD | TBD | Reviews milestone completions. Only person who merges dev into main. |
| Maintainer (Student Leader) | TBD | TBD | Reviews PRs, merges into dev. Does NOT raise PRs or write code. |
| Contributor 1 | TBD | TBD | Works on every issue alongside all other contributors. |
| Contributor 2 | TBD | TBD | Works on every issue alongside all other contributors. |
| Contributor 3 | TBD | TBD | Works on every issue alongside all other contributors. |
| Contributor 4 | TBD | TBD | Works on every issue alongside all other contributors. |

---

## Collaboration Model

Every contributor works on every issue. No one "owns" a module.

### How It Works

For each issue, the team picks one of two approaches:

**Option A: Competitive PRs (individual learning)**
1. All 4 contributors independently implement the issue on their own feature branch.
2. Each raises a separate PR targeting dev.
3. Team reviews all PRs together, discusses tradeoffs.
4. Maintainer merges the best implementation.

**Option B: Collaborative PR (team learning)**
1. Contributors discuss the approach together.
2. They agree on design, split the coding work, and collaborate on one branch.
3. One PR is raised with all contributors as co-authors.
4. Maintainer reviews and merges.

### Branch Naming

**Competitive PRs:**
```
feature/issue-6-ocr-alice
feature/issue-6-ocr-bob
feature/issue-6-ocr-charlie
feature/issue-6-ocr-diana
```

**Collaborative PR:**
```
feature/issue-6-ocr
```

### Co-authoring

```
feat(ocr): integrate Tesseract for printed text extraction

Co-authored-by: Alice <alice@nst.edu>
Co-authored-by: Bob <bob@nst.edu>
Co-authored-by: Charlie <charlie@nst.edu>
Co-authored-by: Diana <diana@nst.edu>
```

---

## Sprint Timeline

| Week | Milestone | Issues | Key Deliverable |
|------|-----------|--------|----------------|
| Week 1 | M1: Scaffold + Ingestion | #1-4 | DB schema, PDF upload, page extraction |
| Week 2 | M2: OCR + Text Extraction | #5-8 | Printed OCR, handwritten OCR, math extraction |
| Week 3 | M3: Layout + Parsing | #9-12 | Question detection, splitter, multi-format, correction UI |
| Week 4 | M4: Topic Tagging + Bank | #13-16 | Syllabus ingestion, topic tagger, question bank, dedup |
| Week 5 | M5: Answers + Verification | #17-20 | Step-by-step solutions, verifier, quality scorer, display |
| Week 6 | M6: Analysis + Prediction | #21-23 | Frequency analysis, prediction agent, visualizations |
| Week 7 | M7: Mocks + Study Plan | #24-27 | Mock generator, test interface, study planner, progress |
| Week 8 | M8: Dashboard + Scraper + Demo | #28-30 | Scraper, dashboard + PWA, E2E + deployment |

---

## Q&A Schedule

Faculty conducts Q&A sessions every 2-3 days per active milestone.

### Rules
- Every contributor must be able to explain every merged PR.
- Come prepared. Read defense questions from MILESTONES.md.
- Code must be pushed before Q&A (faculty will check GitHub).
- If blocked, raise immediately. Do not wait for Q&A.

---

## Review Rules

### For Competitive PRs
- All contributors must review all competing PRs.
- Vote for the best with a thumbs-up reaction.
- After merge, all read the winning implementation.

### For Collaborative PRs
- At least 2 contributors who worked on it must review final code.
- Every co-author must explain the full PR in Q&A.

---

## Daily Standup (Async)

Post in pod channel daily:
1. What I did yesterday
2. What I am doing today
3. Am I blocked on anything

---

NST Engineering - ExamLens AI | Summer Profile Building Drive 2026
