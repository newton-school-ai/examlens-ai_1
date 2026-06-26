"""Question model - an individual question extracted from a paper."""

import enum
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base

if TYPE_CHECKING:
    from src.models.paper import Paper
    from src.models.solution import Solution
    from src.models.topic import Topic


class QuestionType(str, enum.Enum):
    """Broad question format classification."""

    MCQ = "mcq"
    NUMERICAL = "numerical"
    SUBJECTIVE = "subjective"
    FILL_IN_BLANK = "fill_in_blank"
    MATCH = "match"
    UNKNOWN = "unknown"


class Question(Base):
    """A single parsed question extracted from a Paper.

    Holds the raw OCR text, marks, type, and ordering number so that
    the original paper layout can be reconstructed.
    """

    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Content
    text: Mapped[str] = mapped_column(Text, nullable=False)
    question_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    marks: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    negative_marks: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    question_type: Mapped[QuestionType] = mapped_column(
        Enum(QuestionType, name="questiontype", values_callable=lambda obj: [e.value for e in obj]),
        default=QuestionType.UNKNOWN,
        nullable=False,
    )

    # For MCQ - options stored as JSON text (parsed by application)
    options_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Sub-part info
    is_sub_question: Mapped[bool] = mapped_column(default=False, nullable=False)
    parent_question_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("questions.id", ondelete="SET NULL"), nullable=True
    )

    # Year the question appeared (may differ from paper/exam year for cross-year compilations)
    year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # OCR quality
    ocr_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Foreign key
    paper_id: Mapped[int] = mapped_column(
        ForeignKey("papers.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    paper: Mapped["Paper"] = relationship("Paper", back_populates="questions")
    solutions: Mapped[List["Solution"]] = relationship(
        "Solution", back_populates="question", cascade="all, delete-orphan"
    )
    sub_questions: Mapped[List["Question"]] = relationship(
        "Question", back_populates="parent_question"
    )
    parent_question: Mapped[Optional["Question"]] = relationship(
        "Question", remote_side="Question.id", back_populates="sub_questions"
    )
    topics: Mapped[List["Topic"]] = relationship(
        "Topic", secondary="question_topics", back_populates="questions"
    )

    def __repr__(self) -> str:
        return (
            f"<Question id={self.id} paper_id={self.paper_id} "
            f"number={self.question_number} type={self.question_type}>"
        )
