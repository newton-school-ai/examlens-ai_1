"""Seed script – populate ExamLens dev database with realistic sample data.

Usage
-----
    python scripts/seed.py

The script is **idempotent**: running it multiple times will not create
duplicate rows.  It uses ``SELECT ... WHERE`` checks before inserting so
that re-runs are safe on a database that already contains seed data.

Environment
-----------
Reads ``DATABASE_URL`` from the environment (or from a ``.env`` file in
the project root).  Falls back to ``postgresql://localhost/examlens_dev``.
"""

import json
import os
import sys
from pathlib import Path

# Ensure `src.*` imports work when the script is run from any directory.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import create_engine, select  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from src.models import ExamType  # noqa: E402
from src.models import (
    ConfidenceLevel,
    Exam,
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

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://localhost/examlens_dev")


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def get_or_create(session: Session, model, filters: dict, defaults: dict | None = None):
    """Fetch an existing row matching *filters* or create a new one.

    Returns ``(instance, created)`` where *created* is ``True`` when a new
    row was inserted.
    """
    stmt = select(model).filter_by(**filters)
    instance = session.scalars(stmt).first()
    if instance:
        return instance, False
    data = {**filters, **(defaults or {})}
    instance = model(**data)
    session.add(instance)
    session.flush()  # assign PK without committing yet
    return instance, True


# ---------------------------------------------------------------------------
# Seed functions
# ---------------------------------------------------------------------------


def seed_users(session: Session) -> list[User]:
    users_data = [
        dict(
            email="alice@example.com",
            defaults=dict(
                full_name="Alice Sharma",
                google_id="google_alice_001",
                role=UserRole.STUDENT,
                is_active=True,
            ),
        ),
        dict(
            email="bob@example.com",
            defaults=dict(
                full_name="Bob Verma",
                google_id="google_bob_002",
                role=UserRole.CONTRIBUTOR,
                is_active=True,
            ),
        ),
        dict(
            email="charlie@example.com",
            defaults=dict(
                full_name="Charlie Singh",
                google_id="google_charlie_003",
                role=UserRole.STUDENT,
                is_active=True,
            ),
        ),
    ]
    users = []
    for item in users_data:
        user, created = get_or_create(
            session, User, {"email": item["email"]}, item["defaults"]
        )
        users.append(user)
        status = "created" if created else "exists"
        print(f"  User [{status}]: {user.email}")
    return users


def seed_exams(session: Session) -> list[Exam]:
    exams_data = [
        dict(
            name="GATE CS 2024",
            exam_type=ExamType.GATE,
            year=2024,
            description="Graduate Aptitude Test in Engineering – Computer Science 2024",
        ),
        dict(
            name="JEE Mains Jan 2024",
            exam_type=ExamType.JEE_MAINS,
            year=2024,
            description="Joint Entrance Examination Mains – January 2024 session",
        ),
        dict(
            name="JEE Advanced 2023",
            exam_type=ExamType.JEE_ADVANCED,
            year=2023,
            description="Joint Entrance Examination Advanced 2023",
        ),
    ]
    exams = []
    for data in exams_data:
        exam, created = get_or_create(
            session,
            Exam,
            {"name": data["name"], "year": data["year"]},
            {k: v for k, v in data.items() if k not in ("name", "year")},
        )
        exams.append(exam)
        status = "created" if created else "exists"
        print(f"  Exam [{status}]: {exam.name}")
    return exams


def seed_topics(session: Session, exams: list[Exam]) -> list[Topic]:
    gate_exam = exams[0]
    jee_exam = exams[1]

    # GATE topics: Data Structures > Linked Lists > Doubly Linked List
    gate_unit, _ = get_or_create(
        session,
        Topic,
        {"name": "Data Structures", "exam_id": gate_exam.id, "depth": 0},
        {"description": "Core data structure concepts", "parent_id": None},
    )
    gate_topic, _ = get_or_create(
        session,
        Topic,
        {"name": "Linked Lists", "exam_id": gate_exam.id, "depth": 1},
        {
            "description": "Singly, doubly, and circular linked lists",
            "parent_id": gate_unit.id,
        },
    )
    gate_subtopic, _ = get_or_create(
        session,
        Topic,
        {"name": "Doubly Linked List", "exam_id": gate_exam.id, "depth": 2},
        {"parent_id": gate_topic.id},
    )

    # JEE topics: Mathematics > Calculus > Integration
    jee_unit, _ = get_or_create(
        session,
        Topic,
        {"name": "Mathematics", "exam_id": jee_exam.id, "depth": 0},
        {"description": "Mathematics for JEE", "parent_id": None},
    )
    jee_topic, _ = get_or_create(
        session,
        Topic,
        {"name": "Calculus", "exam_id": jee_exam.id, "depth": 1},
        {"description": "Differential and integral calculus", "parent_id": jee_unit.id},
    )
    jee_subtopic, _ = get_or_create(
        session,
        Topic,
        {"name": "Integration", "exam_id": jee_exam.id, "depth": 2},
        {"parent_id": jee_topic.id},
    )

    all_topics = [
        gate_unit,
        gate_topic,
        gate_subtopic,
        jee_unit,
        jee_topic,
        jee_subtopic,
    ]
    for t in all_topics:
        print(f"  Topic: {t.name} (depth={t.depth})")
    return all_topics


def seed_papers(session: Session, exams: list[Exam]) -> list[Paper]:
    papers_data = [
        dict(
            pdf_path="papers/gate_cs_2024.pdf",
            exam_id=exams[0].id,
            defaults=dict(
                page_count=32,
                original_filename="GATE_CS_2024.pdf",
                file_size_bytes=2_048_000,
                ocr_status="done",
                notes="Official GATE CS 2024 paper – fully parsed",
            ),
        ),
        dict(
            pdf_path="papers/jee_mains_jan_2024.pdf",
            exam_id=exams[1].id,
            defaults=dict(
                page_count=24,
                original_filename="JEE_Mains_Jan_2024.pdf",
                file_size_bytes=1_536_000,
                ocr_status="done",
                notes="JEE Mains January 2024 – Mathematics section",
            ),
        ),
        dict(
            pdf_path="papers/jee_advanced_2023_p1.pdf",
            exam_id=exams[2].id,
            defaults=dict(
                page_count=28,
                original_filename="JEE_Advanced_2023_Paper1.pdf",
                file_size_bytes=3_072_000,
                ocr_status="processing",
                notes="JEE Advanced 2023 Paper 1 – OCR in progress",
            ),
        ),
    ]
    papers = []
    for item in papers_data:
        paper, created = get_or_create(
            session,
            Paper,
            {"pdf_path": item["pdf_path"], "exam_id": item["exam_id"]},
            item["defaults"],
        )
        papers.append(paper)
        status = "created" if created else "exists"
        print(f"  Paper [{status}]: {paper.pdf_path}")
    return papers


def seed_questions(
    session: Session, papers: list[Paper], topics: list[Topic]
) -> list[Question]:
    gate_paper = papers[0]
    jee_paper = papers[1]
    gate_subtopic = topics[2]  # Doubly Linked List
    jee_subtopic = topics[5]  # Integration

    questions_data = [
        dict(
            text="Which of the following is correct about doubly linked lists?\n"
            "(A) Each node has one pointer\n"
            "(B) Each node has two pointers: next and prev\n"
            "(C) Traversal is only forward\n"
            "(D) Insertion at head takes O(n)",
            question_number=1,
            paper_id=gate_paper.id,
            defaults=dict(
                marks=1.0,
                negative_marks=0.33,
                question_type=QuestionType.MCQ,
                options_json=json.dumps(["A", "B", "C", "D"]),
                year=2024,
                ocr_confidence=0.97,
                is_sub_question=False,
            ),
        ),
        dict(
            text="The time complexity of deleting a node from the middle of a doubly linked list, "
            "given a pointer to that node, is:",
            question_number=2,
            paper_id=gate_paper.id,
            defaults=dict(
                marks=2.0,
                negative_marks=0.66,
                question_type=QuestionType.MCQ,
                options_json=json.dumps(["O(1)", "O(log n)", "O(n)", "O(n²)"]),
                year=2024,
                ocr_confidence=0.95,
                is_sub_question=False,
            ),
        ),
        dict(
            text=r"Evaluate $\int_0^1 x^2 \,dx$",
            question_number=1,
            paper_id=jee_paper.id,
            defaults=dict(
                marks=4.0,
                negative_marks=1.0,
                question_type=QuestionType.NUMERICAL,
                year=2024,
                ocr_confidence=0.91,
                is_sub_question=False,
            ),
        ),
        dict(
            text=r"Find the area enclosed between $y = x^2$ and $y = x$ for $0 \le x \le 1$.",
            question_number=2,
            paper_id=jee_paper.id,
            defaults=dict(
                marks=4.0,
                negative_marks=1.0,
                question_type=QuestionType.SUBJECTIVE,
                year=2024,
                ocr_confidence=0.89,
                is_sub_question=False,
            ),
        ),
    ]

    questions = []
    for item in questions_data:
        q, created = get_or_create(
            session,
            Question,
            {
                "text": item["text"],
                "question_number": item["question_number"],
                "paper_id": item["paper_id"],
            },
            item["defaults"],
        )
        questions.append(q)
        status = "created" if created else "exists"
        print(f"  Question [{status}]: Q{q.question_number} (paper_id={q.paper_id})")

    # Attach topics to questions if not already done
    session.flush()
    gate_q1, gate_q2, jee_q1, jee_q2 = questions
    for q in [gate_q1, gate_q2]:
        if gate_subtopic not in q.topics:
            q.topics.append(gate_subtopic)
    for q in [jee_q1, jee_q2]:
        if jee_subtopic not in q.topics:
            q.topics.append(jee_subtopic)

    return questions


def seed_solutions(session: Session, questions: list[Question]) -> list[Solution]:
    solutions_data = [
        dict(
            question_id=questions[0].id,
            defaults=dict(
                answer="B",
                steps_json=json.dumps(
                    [
                        "A doubly linked list node stores data, a *next* pointer, and a *prev* pointer.",
                        "This allows O(1) bidirectional traversal.",
                        "Correct answer: B.",
                    ]
                ),
                explanation="Each node in a DLL has two pointers: `next` (forward) and `prev` (backward).",
                confidence=ConfidenceLevel.HIGH,
                confidence_score=0.98,
                is_verified=True,
                verification_source="GATE 2024 official answer key",
                model_used="llama-3.1-70b-versatile",
            ),
        ),
        dict(
            question_id=questions[1].id,
            defaults=dict(
                answer="O(1)",
                steps_json=json.dumps(
                    [
                        "Given a pointer to the node, we can directly update prev.next and next.prev.",
                        "No traversal is needed, so time complexity is O(1).",
                    ]
                ),
                explanation="With a direct pointer, re-linking neighbours is O(1).",
                confidence=ConfidenceLevel.HIGH,
                confidence_score=0.99,
                is_verified=True,
                verification_source="GATE 2024 official answer key",
                model_used="llama-3.1-70b-versatile",
            ),
        ),
        dict(
            question_id=questions[2].id,
            defaults=dict(
                answer="1/3",
                steps_json=json.dumps(
                    [
                        r"$\int_0^1 x^2 \,dx = \left[\frac{x^3}{3}\right]_0^1$",
                        r"$= \frac{1}{3} - 0 = \frac{1}{3}$",
                    ]
                ),
                explanation=r"Apply the power rule: $\int x^n dx = \frac{x^{n+1}}{n+1} + C$.",
                confidence=ConfidenceLevel.HIGH,
                confidence_score=0.99,
                is_verified=False,
                model_used="llama-3.1-70b-versatile",
            ),
        ),
        dict(
            question_id=questions[3].id,
            defaults=dict(
                answer="1/6",
                steps_json=json.dumps(
                    [
                        r"Intersection points: $x^2 = x \Rightarrow x = 0, 1$",
                        r"Area $= \int_0^1 (x - x^2)\,dx$",
                        r"$= \left[\frac{x^2}{2} - \frac{x^3}{3}\right]_0^1 = \frac{1}{2} - \frac{1}{3} = \frac{1}{6}$",
                    ]
                ),
                explanation=r"Subtract the lower curve from the upper curve and integrate.",
                confidence=ConfidenceLevel.MEDIUM,
                confidence_score=0.87,
                is_verified=False,
                model_used="llama-3.1-70b-versatile",
            ),
        ),
    ]

    solutions = []
    for item in solutions_data:
        sol, created = get_or_create(
            session,
            Solution,
            {"question_id": item["question_id"]},
            item["defaults"],
        )
        solutions.append(sol)
        status = "created" if created else "exists"
        print(
            f"  Solution [{status}]: question_id={sol.question_id} confidence={sol.confidence}"
        )
    return solutions


def seed_mock_tests(
    session: Session, users: list[User], questions: list[Question]
) -> list[MockTest]:
    student = users[0]  # Alice
    mock, created = get_or_create(
        session,
        MockTest,
        {"title": "GATE CS Practice Test #1", "user_id": student.id},
        dict(
            generated_paper_json=json.dumps([q.id for q in questions[:2]]),
            status="submitted",
            duration_minutes=30,
            score=3.0,
            max_score=3.0,
            answers_json=json.dumps(
                {str(questions[0].id): "B", str(questions[1].id): "O(1)"}
            ),
        ),
    )
    status = "created" if created else "exists"
    print(f"  MockTest [{status}]: {mock.title} (user={student.email})")
    return [mock]


def seed_study_plans(session: Session, users: list[User]) -> list[StudyPlan]:
    student = users[0]  # Alice
    plan, created = get_or_create(
        session,
        StudyPlan,
        {"title": "GATE CS 2025 – 90-Day Plan", "user_id": student.id},
        dict(
            target_exam_name="GATE CS 2025",
            total_days=90,
            available_hours_per_day=3.0,
            weak_topics_json=json.dumps(["Data Structures", "Algorithms"]),
            is_active=True,
            daily_plan_json=json.dumps(
                [
                    {"day": 1, "topics": ["Arrays", "Linked Lists"], "hours": 3},
                    {"day": 2, "topics": ["Stacks", "Queues"], "hours": 3},
                ]
            ),
        ),
    )
    status = "created" if created else "exists"
    print(f"  StudyPlan [{status}]: {plan.title} (user={student.email})")
    return [plan]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    print(f"Connecting to: {DATABASE_URL}\n")
    engine = create_engine(DATABASE_URL, echo=False)

    with Session(engine) as session:
        print("=== Seeding Users ===")
        users = seed_users(session)

        print("\n=== Seeding Exams ===")
        exams = seed_exams(session)

        print("\n=== Seeding Topics ===")
        topics = seed_topics(session, exams)

        print("\n=== Seeding Papers ===")
        papers = seed_papers(session, exams)

        print("\n=== Seeding Questions ===")
        questions = seed_questions(session, papers, topics)

        print("\n=== Seeding Solutions ===")
        seed_solutions(session, questions)

        print("\n=== Seeding Mock Tests ===")
        seed_mock_tests(session, users, questions)

        print("\n=== Seeding Study Plans ===")
        seed_study_plans(session, users)

        session.commit()

    print("\n✅  Seed complete.")


if __name__ == "__main__":
    main()
