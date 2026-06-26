"""Paper model - represents a single uploaded question paper PDF."""

from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base

if TYPE_CHECKING:
    from src.models.exam import Exam
    from src.models.question import Question


class Paper(Base):
    """A single uploaded question paper (one PDF / image set).

    Linked to an Exam and holds all extracted Questions once the
    ingestion pipeline has run.
    """

    __tablename__ = "papers"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Storage
    pdf_path: Mapped[str] = mapped_column(String(512), nullable=False)
    page_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    original_filename: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    file_size_bytes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # OCR / ingestion status
    ocr_status: Mapped[str] = mapped_column(
        String(32), default="pending", nullable=False
    )  # pending | processing | done | failed
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Foreign key
    exam_id: Mapped[int] = mapped_column(
        ForeignKey("exams.id", ondelete="CASCADE"), nullable=False, index=True
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
    exam: Mapped["Exam"] = relationship("Exam", back_populates="papers")
    questions: Mapped[List["Question"]] = relationship(
        "Question", back_populates="paper", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return (
            f"<Paper id={self.id} exam_id={self.exam_id} pages={self.page_count} "
            f"status={self.ocr_status!r}>"
        )
