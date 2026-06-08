# Contributing to ExamLens AI

Branch strategy, PR workflow, pod roles, and coding standards.

---

## Branch Strategy

```
main  (stable - only receives milestone-complete merges from dev)
 |
 +-- dev  (all feature branches merge here)
      |
      +-- feature/issue-N-short-name  (one branch per issue)
```

### Rules

1. Never push to main directly.
2. All PRs target dev.
3. Maintainer merges to main only after full milestone review.
4. One branch per issue. One PR per branch.

### Branch Naming

- Features: `feature/issue-6-tesseract-ocr`
- Fixes: `fix/issue-10-question-split`
- Docs: `docs/issue-2-db-schema`

---

## PR Workflow

### Before Opening a PR

1. Branch is up to date with dev:
   ```bash
   git checkout dev && git pull origin dev
   git checkout feature/issue-6-tesseract-ocr
   git rebase dev
   ```
2. All tests pass: `pytest tests/`
3. Code is formatted: `black src/ tests/` and `isort src/ tests/`
4. No lint errors: `flake8 src/ tests/`

### Review Process

**Competitive PRs (multiple PRs per issue):**
1. Each contributor opens their own PR targeting dev.
2. All other contributors review all competing PRs.
3. Minimum 2 approvals required.
4. Maintainer merges the best implementation.

**Collaborative PRs (one PR per issue):**
1. Team collaborates on one branch, one PR targeting dev.
2. Add all contributors as co-authors in commit message.
3. Minimum 2 approvals from team members who contributed.
4. Maintainer reviews and merges.

---

## Pod Roles

| Role | Permission | Responsibility |
|------|-----------|---------------|
| Faculty | Admin (org owner) | Reviews milestones. Only person who merges dev into main. |
| Maintainer | Maintain | Reviews PRs, merges into dev. Does NOT write code or raise PRs. |
| Contributor | Write | Works on every issue. Raises PRs (individually or collaboratively). Reviews peers' PRs. |

All 4 contributors work on every issue. No module ownership. Faculty Q&A every 2-3 days.

---

## Coding Standards

### Python

- Python 3.10+ required.
- Formatter: `black` (line length 88).
- Import sorting: `isort` with black profile.
- Linter: `flake8` with max line length 88.
- Type hints required on all function signatures.
- Docstrings on all public functions (Google style).

### Naming

- Files: `snake_case.py`
- Classes: `PascalCase`
- Functions/variables: `snake_case`
- Constants: `UPPER_SNAKE_CASE`

### Commits

Format: `type(scope): description`
Types: feat, fix, docs, test, refactor, chore
Examples: `feat(ocr): add Tesseract printed text extraction`, `fix(parser): handle missing marks field`

### Frontend (React)

- Functional components with hooks only.
- Tailwind CSS - no separate CSS files.
- Component files: `PascalCase.jsx`

---

## Environment Setup

See [DEVELOPMENT_GUIDE.md](DEVELOPMENT_GUIDE.md) for full setup instructions.

---

NST Engineering - ExamLens AI | Summer Profile Building Drive 2026
