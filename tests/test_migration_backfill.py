"""Regression tests for the milestone-one Alembic backfill migration."""

import sys
import types
from importlib import util
from pathlib import Path

import pytest
from sqlalchemy import Column, Integer, MetaData, String, Table, create_engine, text
from sqlalchemy.orm import Session

MIGRATION_PATH = (
    Path(__file__).resolve().parents[1]
    / "alembic"
    / "versions"
    / "4f3c1a2b9d10_align_milestone_one_schema.py"
)

fake_alembic = types.ModuleType("alembic")
fake_alembic.op = types.SimpleNamespace()
original_alembic = sys.modules.get("alembic")
sys.modules["alembic"] = fake_alembic

spec = util.spec_from_file_location("migration_4f3c1a2b9d10", MIGRATION_PATH)
assert spec is not None and spec.loader is not None
MIGRATION_MODULE = util.module_from_spec(spec)
spec.loader.exec_module(MIGRATION_MODULE)

if original_alembic is None:
    sys.modules.pop("alembic", None)
else:
    sys.modules["alembic"] = original_alembic


@pytest.fixture
def engine():
    """SQLite engine with a minimal legacy schema for migration helpers."""
    eng = create_engine("sqlite:///:memory:")
    metadata = MetaData()

    Table(
        "exams",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("name", String(255), nullable=False),
        Column("exam_type", String(50), nullable=False),
        Column("year", Integer, nullable=False),
        Column("description", String(255), nullable=True),
    )
    Table("papers", metadata, Column("id", Integer, primary_key=True))
    Table("mock_tests", metadata, Column("id", Integer, primary_key=True))
    Table("study_plans", metadata, Column("id", Integer, primary_key=True))
    Table(
        "solutions",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("question_id", Integer, nullable=False),
        Column("answer", String(20), nullable=False),
    )
    metadata.create_all(eng)
    yield eng
    metadata.drop_all(eng)


@pytest.fixture
def session(engine):
    """Transactional session used to inspect the helper side effects."""
    connection = engine.connect()
    transaction = connection.begin()
    sess = Session(bind=connection)
    yield sess
    sess.close()
    transaction.rollback()
    connection.close()


def test_ensure_legacy_exam_inserts_fallback_row_for_legacy_data(session):
    """Legacy dependent rows should trigger a fallback exam insert."""
    session.execute(text("INSERT INTO papers (id) VALUES (1)"))
    session.execute(text("INSERT INTO mock_tests (id) VALUES (1)"))
    session.commit()

    MIGRATION_MODULE._ensure_legacy_exam(session)
    session.commit()

    rows = session.execute(text("SELECT name, exam_type, year FROM exams")).fetchall()
    assert rows == [("Legacy Exam", "other", 1970)]


def test_ensure_legacy_exam_leaves_clean_database_empty(session):
    """An empty clean database should not get a synthetic exam row."""
    MIGRATION_MODULE._ensure_legacy_exam(session)
    session.commit()

    row_count = session.execute(text("SELECT COUNT(*) FROM exams")).scalar_one()
    assert row_count == 0


def test_deduplicate_solutions_keeps_latest_solution_per_question(session):
    """The migration should remove older duplicate solutions before the unique constraint."""
    session.execute(text(
        """
        INSERT INTO solutions (id, question_id, answer) VALUES
        (1, 10, 'first'),
        (2, 10, 'latest'),
        (3, 11, 'only')
        """
    ))
    session.commit()

    MIGRATION_MODULE._deduplicate_solutions(session)
    session.commit()

    rows = session.execute(
        text("SELECT id, question_id, answer FROM solutions ORDER BY id")
    ).fetchall()
    assert rows == [(2, 10, "latest"), (3, 11, "only")]
