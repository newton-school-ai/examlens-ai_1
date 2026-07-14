"""Align database schema with Milestone 1 acceptance criteria.

Revision ID: 4f3c1a2b9d10
Revises: ebe6e67df6bf
"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "4f3c1a2b9d10"
down_revision: Union[str, None] = "ebe6e67df6bf"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("auth_provider", sa.String(50), nullable=True))

    op.add_column("papers", sa.Column("file_hash", sa.String(64), nullable=True))
    op.add_column("papers", sa.Column("year", sa.Integer(), nullable=True))
    op.add_column("papers", sa.Column("session", sa.String(100), nullable=True))
    op.add_column("papers", sa.Column("total_marks", sa.Float(), nullable=True))
    op.execute(
        "UPDATE papers SET year = exams.year FROM exams WHERE papers.exam_id = exams.id"
    )
    op.alter_column("papers", "year", nullable=False)
    op.create_index("ix_papers_file_hash", "papers", ["file_hash"], unique=True)

    op.alter_column(
        "questions",
        "question_number",
        existing_type=sa.Integer(),
        type_=sa.String(32),
        postgresql_using="question_number::text",
    )
    op.alter_column(
        "questions",
        "options_json",
        existing_type=sa.Text(),
        type_=postgresql.JSON(astext_type=sa.Text()),
        postgresql_using="options_json::json",
    )
    op.add_column("questions", sa.Column("sub_parts", sa.JSON(), nullable=True))
    op.add_column("questions", sa.Column("image_path", sa.String(512), nullable=True))

    op.alter_column(
        "solutions",
        "steps_json",
        existing_type=sa.Text(),
        type_=postgresql.JSON(astext_type=sa.Text()),
        postgresql_using="steps_json::json",
    )
    op.add_column("solutions", sa.Column("latex", sa.Text(), nullable=True))
    op.create_unique_constraint(
        "uq_solutions_question_id", "solutions", ["question_id"]
    )

    op.add_column(
        "topics",
        sa.Column("frequency_count", sa.Integer(), server_default="0", nullable=False),
    )

    op.add_column("mock_tests", sa.Column("exam_id", sa.Integer(), nullable=True))
    op.execute("UPDATE mock_tests SET exam_id = (SELECT MIN(id) FROM exams)")
    op.alter_column("mock_tests", "exam_id", nullable=False)
    op.create_foreign_key(
        "fk_mock_tests_exam_id",
        "mock_tests",
        "exams",
        ["exam_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_mock_tests_exam_id", "mock_tests", ["exam_id"])

    op.add_column("study_plans", sa.Column("exam_id", sa.Integer(), nullable=True))
    op.execute("UPDATE study_plans SET exam_id = (SELECT MIN(id) FROM exams)")
    op.alter_column("study_plans", "exam_id", nullable=False)
    op.create_foreign_key(
        "fk_study_plans_exam_id",
        "study_plans",
        "exams",
        ["exam_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_study_plans_exam_id", "study_plans", ["exam_id"])


def downgrade() -> None:
    op.drop_index("ix_study_plans_exam_id", table_name="study_plans")
    op.drop_constraint("fk_study_plans_exam_id", "study_plans", type_="foreignkey")
    op.drop_column("study_plans", "exam_id")
    op.drop_index("ix_mock_tests_exam_id", table_name="mock_tests")
    op.drop_constraint("fk_mock_tests_exam_id", "mock_tests", type_="foreignkey")
    op.drop_column("mock_tests", "exam_id")
    op.drop_column("topics", "frequency_count")
    op.drop_constraint("uq_solutions_question_id", "solutions", type_="unique")
    op.drop_column("solutions", "latex")
    op.alter_column(
        "solutions", "steps_json", type_=sa.Text(), postgresql_using="steps_json::text"
    )
    op.drop_column("questions", "image_path")
    op.drop_column("questions", "sub_parts")
    op.alter_column(
        "questions",
        "options_json",
        type_=sa.Text(),
        postgresql_using="options_json::text",
    )
    op.alter_column(
        "questions",
        "question_number",
        type_=sa.Integer(),
        postgresql_using="question_number::integer",
    )
    op.drop_index("ix_papers_file_hash", table_name="papers")
    op.drop_column("papers", "total_marks")
    op.drop_column("papers", "session")
    op.drop_column("papers", "year")
    op.drop_column("papers", "file_hash")
    op.drop_column("users", "auth_provider")
