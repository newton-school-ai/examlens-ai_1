"""Solution model - step-by-step answer generated for a question."""

import enum
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base

if TYPE_CHECKING:
    from src.models.question import Question


class ConfidenceLevel(str, enum.Enum):
    """Confidence tier for a generated solution."""

    HIGH = "high"  # Verified against official answer key
    MEDIUM = "medium"  # LLM is confident but not externally verified
    LOW = "low"  # Uncertain / flagged for review


class Solution(Base):
    """A generated and optionally verified solution for a Question.

    Stores the answer, step-by-step explanation (may contain LaTeX),
    confidence level, and whether it was verified against an official key.
    """

    __tablename__ = "solutions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Content
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    steps_json: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )  # JSON list of step strings (may include LaTeX)
    explanation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Quality signals
    confidence: Mapped[ConfidenceLevel] = mapped_column(
        Enum(
            ConfidenceLevel,
            name="confidencelevel",
            values_callable=lambda obj: [e.value for e in obj],
        ),
        default=ConfidenceLevel.MEDIUM,
        nullable=False,
    )
    confidence_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    verification_source: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # LLM metadata
    model_used: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Foreign key
    question_id: Mapped[int] = mapped_column(
        ForeignKey("questions.id", ondelete="CASCADE"), nullable=False, index=True
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
    question: Mapped["Question"] = relationship("Question", back_populates="solutions")

    def __repr__(self) -> str:
        return (
            f"<Solution id={self.id} question_id={self.question_id} "
            f"confidence={self.confidence} verified={self.is_verified}>"
        )
