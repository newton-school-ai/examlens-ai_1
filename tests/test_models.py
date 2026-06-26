"""Unit tests for Issue #2 – SQLAlchemy models.

Covers three required areas:
  1. Model creation – can we instantiate each model with required fields?
  2. Relationships – do FK / ORM relationships resolve correctly?
  3. Constraints – do unique / not-null constraints fire as expected?

Uses an **in-memory SQLite** database so no PostgreSQL installation is needed
to run the test suite locally.

Run with:
    pytest tests/test_models.py -v
"""

import json

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.models import (
    Base,
    ConfidenceLevel,
    Exam,
    ExamType,
    MockTest,
    Paper,
    Question,
    QuestionType,
    Solution,
    StudyPlan,
    Topic,
    User,
    UserRole,
)

# ---------------------------------------------------------------------------
# Engine / Session fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def engine():
    """In-memory SQLite engine with FK enforcement enabled."""
    eng = create_engine("sqlite:///:memory:", echo=False)

    # SQLite does not enforce FK constraints by default – enable them.
    @event.listens_for(eng, "connect")
    def set_sqlite_pragma(dbapi_conn, _):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(eng)
    yield eng
    Base.metadata.drop_all(eng)


@pytest.fixture
def session(engine):
    """Transactional test session – rolls back after each test."""
    connection = engine.connect()
    transaction = connection.begin()
    sess = Session(bind=connection)
    yield sess
    sess.close()
    transaction.rollback()
    connection.close()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_user(session: Session, email: str = "test@example.com", **kwargs) -> User:
    u = User(
        email=email,
        role=kwargs.get("role", UserRole.STUDENT),
        **{k: v for k, v in kwargs.items() if k != "role"}
    )
    session.add(u)
    session.flush()
    return u


def make_exam(session: Session, name: str = "GATE CS 2024", year: int = 2024) -> Exam:
    e = Exam(name=name, exam_type=ExamType.GATE, year=year)
    session.add(e)
    session.flush()
    return e


def make_paper(session: Session, exam: Exam, pdf_path: str = "test.pdf") -> Paper:
    p = Paper(pdf_path=pdf_path, page_count=10, exam_id=exam.id)
    session.add(p)
    session.flush()
    return p


def make_question(
    session: Session, paper: Paper, text: str = "What is 2+2?", number: int = 1
) -> Question:
    q = Question(
        text=text,
        question_number=number,
        question_type=QuestionType.MCQ,
        marks=1.0,
        paper_id=paper.id,
    )
    session.add(q)
    session.flush()
    return q


def make_solution(session: Session, question: Question) -> Solution:
    s = Solution(
        answer="4",
        steps_json=json.dumps(["2 + 2 = 4"]),
        confidence=ConfidenceLevel.HIGH,
        question_id=question.id,
    )
    session.add(s)
    session.flush()
    return s


def make_topic(
    session: Session, exam: Exam, name: str = "Algorithms", depth: int = 0
) -> Topic:
    t = Topic(name=name, depth=depth, exam_id=exam.id)
    session.add(t)
    session.flush()
    return t


# ===========================================================================
# 1. Model creation tests
# ===========================================================================


class TestModelCreation:
    """Verify each model can be created with its minimum required fields."""

    def test_create_user(self, session):
        user = make_user(session, email="alice@test.com", full_name="Alice")
        assert user.id is not None
        assert user.email == "alice@test.com"
        assert user.role == UserRole.STUDENT
        assert user.is_active is True

    def test_create_exam(self, session):
        exam = make_exam(session)
        assert exam.id is not None
        assert exam.exam_type == ExamType.GATE
        assert exam.year == 2024

    def test_create_paper(self, session):
        exam = make_exam(session, name="JEE 2024", year=2024)
        paper = make_paper(session, exam, pdf_path="jee.pdf")
        assert paper.id is not None
        assert paper.exam_id == exam.id
        assert paper.ocr_status == "pending"

    def test_create_question_with_all_required_fields(self, session):
        exam = make_exam(session, name="GATE 2023", year=2023)
        paper = make_paper(session, exam)
        q = make_question(session, paper, text="Explain BFS.", number=5)
        assert q.id is not None
        assert q.question_number == 5
        assert q.question_type == QuestionType.MCQ
        assert q.paper_id == paper.id

    def test_question_stores_year_field(self, session):
        """Issue #2 explicitly requires a 'year' column on Question."""
        exam = make_exam(session)
        paper = make_paper(session, exam)
        q = Question(
            text="Sample question",
            question_number=1,
            question_type=QuestionType.NUMERICAL,
            marks=2.0,
            paper_id=paper.id,
            year=2024,
        )
        session.add(q)
        session.flush()
        assert q.year == 2024

    def test_create_solution(self, session):
        exam = make_exam(session)
        paper = make_paper(session, exam)
        q = make_question(session, paper)
        sol = make_solution(session, q)
        assert sol.id is not None
        assert sol.confidence == ConfidenceLevel.HIGH
        assert sol.answer == "4"

    def test_solution_stores_steps_as_json(self, session):
        """Solution.steps_json should round-trip through json.loads."""
        exam = make_exam(session)
        paper = make_paper(session, exam)
        q = make_question(session, paper)
        steps = ["Step 1: identify", r"Step 2: $\int x dx = x^2/2$"]
        sol = Solution(
            answer="done",
            steps_json=json.dumps(steps),
            confidence=ConfidenceLevel.MEDIUM,
            question_id=q.id,
        )
        session.add(sol)
        session.flush()
        assert json.loads(sol.steps_json) == steps

    def test_create_topic_with_hierarchy(self, session):
        exam = make_exam(session)
        unit = make_topic(session, exam, name="Math", depth=0)
        topic = Topic(name="Calculus", depth=1, exam_id=exam.id, parent_id=unit.id)
        session.add(topic)
        session.flush()
        subtopic = Topic(
            name="Integration", depth=2, exam_id=exam.id, parent_id=topic.id
        )
        session.add(subtopic)
        session.flush()
        assert subtopic.id is not None
        assert subtopic.parent_id == topic.id

    def test_create_mock_test(self, session):
        user = make_user(session, email="mock@test.com")
        mt = MockTest(user_id=user.id, status="draft")
        session.add(mt)
        session.flush()
        assert mt.id is not None
        assert mt.status == "draft"

    def test_create_study_plan(self, session):
        user = make_user(session, email="plan@test.com")
        sp = StudyPlan(
            user_id=user.id,
            title="90-Day Plan",
            target_exam_name="GATE CS",
            total_days=90,
        )
        session.add(sp)
        session.flush()
        assert sp.id is not None
        assert sp.is_active is True


# ===========================================================================
# 2. Relationship tests
# ===========================================================================


class TestRelationships:
    """Verify ORM relationships resolve to the correct objects."""

    def test_exam_paper_relationship(self, session):
        exam = make_exam(session)
        p1 = make_paper(session, exam, pdf_path="a.pdf")
        p2 = make_paper(session, exam, pdf_path="b.pdf")
        session.refresh(exam)
        assert len(exam.papers) == 2
        assert p1 in exam.papers
        assert p2 in exam.papers

    def test_paper_question_relationship(self, session):
        exam = make_exam(session)
        paper = make_paper(session, exam)
        q = make_question(session, paper)
        session.refresh(paper)
        assert len(paper.questions) == 1
        assert paper.questions[0].id == q.id
        # Reverse relationship
        assert q.paper.id == paper.id

    def test_question_solution_relationship(self, session):
        exam = make_exam(session)
        paper = make_paper(session, exam)
        q = make_question(session, paper)
        sol = make_solution(session, q)
        session.refresh(q)
        assert len(q.solutions) == 1
        assert q.solutions[0].id == sol.id
        assert sol.question.id == q.id

    def test_topic_hierarchy_relationship(self, session):
        exam = make_exam(session)
        parent = make_topic(session, exam, name="DS", depth=0)
        child = Topic(name="Arrays", depth=1, exam_id=exam.id, parent_id=parent.id)
        session.add(child)
        session.flush()
        session.refresh(parent)
        assert child in parent.children
        assert child.parent.id == parent.id

    def test_question_topic_many_to_many(self, session):
        exam = make_exam(session)
        paper = make_paper(session, exam)
        q = make_question(session, paper)
        t1 = make_topic(session, exam, name="Topic A")
        t2 = make_topic(session, exam, name="Topic B")
        q.topics.extend([t1, t2])
        session.flush()
        session.refresh(q)
        assert t1 in q.topics
        assert t2 in q.topics
        assert q in t1.questions

    def test_user_mock_test_relationship(self, session):
        user = make_user(session, email="user@rel.com")
        mt = MockTest(user_id=user.id, status="draft")
        session.add(mt)
        session.flush()
        session.refresh(user)
        assert len(user.mock_tests) == 1
        assert mt.user.id == user.id

    def test_user_study_plan_relationship(self, session):
        user = make_user(session, email="plan@rel.com")
        sp = StudyPlan(user_id=user.id, title="My Plan")
        session.add(sp)
        session.flush()
        session.refresh(user)
        assert sp in user.study_plans

    def test_cascade_delete_paper_removes_questions(self, session):
        """Deleting a Paper should cascade-delete its Questions."""
        exam = make_exam(session)
        paper = make_paper(session, exam)
        q = make_question(session, paper)
        qid = q.id
        session.delete(paper)
        session.flush()
        assert session.get(Question, qid) is None

    def test_sub_question_parent_relationship(self, session):
        exam = make_exam(session)
        paper = make_paper(session, exam)
        parent_q = make_question(session, paper, text="Part A", number=1)
        sub_q = Question(
            text="Part A (i)",
            question_number=1,
            question_type=QuestionType.SUBJECTIVE,
            paper_id=paper.id,
            is_sub_question=True,
            parent_question_id=parent_q.id,
        )
        session.add(sub_q)
        session.flush()
        session.refresh(parent_q)
        assert sub_q in parent_q.sub_questions
        assert sub_q.parent_question.id == parent_q.id


# ===========================================================================
# 3. Constraint tests
# ===========================================================================


class TestConstraints:
    """Verify NOT NULL and UNIQUE database constraints are enforced."""

    def test_user_email_unique_constraint(self, session):
        make_user(session, email="dup@test.com")
        session.flush()
        with pytest.raises((IntegrityError, Exception)):
            make_user(session, email="dup@test.com")
            session.flush()

    def test_question_requires_paper_id(self, session):
        """Question.paper_id is NOT NULL — omitting it should raise."""
        with pytest.raises(Exception):
            q = Question(text="orphan", question_type=QuestionType.MCQ)
            session.add(q)
            session.flush()

    def test_solution_requires_question_id(self, session):
        """Solution.question_id is NOT NULL — omitting it should raise."""
        with pytest.raises(Exception):
            s = Solution(answer="x", confidence=ConfidenceLevel.LOW)
            session.add(s)
            session.flush()

    def test_paper_requires_exam_id(self, session):
        """Paper.exam_id is NOT NULL — omitting it should raise."""
        with pytest.raises(Exception):
            p = Paper(pdf_path="no_exam.pdf", page_count=5)
            session.add(p)
            session.flush()

    def test_confidence_level_enum_values(self, session):
        """ConfidenceLevel enum must have exactly high/medium/low."""
        assert set(ConfidenceLevel) == {
            ConfidenceLevel.HIGH,
            ConfidenceLevel.MEDIUM,
            ConfidenceLevel.LOW,
        }

    def test_question_type_enum_values(self, session):
        """QuestionType enum must include MCQ, subjective, numerical."""
        expected = {QuestionType.MCQ, QuestionType.SUBJECTIVE, QuestionType.NUMERICAL}
        assert expected.issubset(set(QuestionType))

    def test_solution_confidence_defaults_to_medium(self, session):
        exam = make_exam(session)
        paper = make_paper(session, exam)
        q = make_question(session, paper)
        sol = Solution(answer="42", question_id=q.id)
        session.add(sol)
        session.flush()
        assert sol.confidence == ConfidenceLevel.MEDIUM

    def test_mock_test_status_defaults_to_draft(self, session):
        user = make_user(session, email="draft@test.com")
        mt = MockTest(user_id=user.id)
        session.add(mt)
        session.flush()
        assert mt.status == "draft"

    def test_study_plan_is_active_defaults_true(self, session):
        user = make_user(session, email="active@test.com")
        sp = StudyPlan(user_id=user.id)
        session.add(sp)
        session.flush()
        assert sp.is_active is True
