"""MockTest model - a generated mock exam taken by a user."""

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base

if TYPE_CHECKING:
    from src.models.user import User


class MockTest(Base):
    """A mock exam paper generated for and taken by a User.

    ``generated_paper_json`` holds the serialised list of selected
    question IDs and their order so the test can be reconstructed.
    Scores and timing metadata are stored here once the test is
    submitted.
    """

    __tablename__ = "mock_tests"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Generated paper content - JSON list of question IDs with metadata
    generated_paper_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Test state
    status: Mapped[str] = mapped_column(
        String(32), default="draft", nullable=False
    )  # draft | in_progress | submitted | graded

    # Timing
    duration_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    submitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Grading
    score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    max_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    answers_json: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )  # JSON map of question_id -> user_answer

    # Foreign key
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
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
    user: Mapped["User"] = relationship("User", back_populates="mock_tests")

    def __repr__(self) -> str:
        return (
            f"<MockTest id={self.id} user_id={self.user_id} "
            f"status={self.status!r} score={self.score}>"
        )
