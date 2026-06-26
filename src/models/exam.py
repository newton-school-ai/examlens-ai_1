"""Exam model - represents an exam type such as GATE, JEE, or a university exam."""

import enum
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import DateTime, Enum, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base

if TYPE_CHECKING:
    from src.models.paper import Paper
    from src.models.topic import Topic


class ExamType(str, enum.Enum):
    """Broad category of an exam."""

    GATE = "gate"
    JEE_MAINS = "jee_mains"
    JEE_ADVANCED = "jee_advanced"
    UNIVERSITY = "university"
    OTHER = "other"


class Exam(Base):
    """Represents a named examination series (e.g., GATE CS 2024).

    An Exam groups multiple Papers (one per year / session) and provides
    the anchor for syllabus topics and analytics.
    """

    __tablename__ = "exams"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    exam_type: Mapped[ExamType] = mapped_column(
        Enum(ExamType, name="examtype", values_callable=lambda obj: [e.value for e in obj]), nullable=False
    )
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

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
    papers: Mapped[List["Paper"]] = relationship(
        "Paper", back_populates="exam", cascade="all, delete-orphan"
    )
    topics: Mapped[List["Topic"]] = relationship(
        "Topic", back_populates="exam", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Exam id={self.id} name={self.name!r} year={self.year} type={self.exam_type}>"
