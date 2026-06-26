"""Topic model - hierarchical syllabus topic with self-referencing parent FK."""

from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import DateTime, ForeignKey, String, Table, Text, Column, Integer, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base

if TYPE_CHECKING:
    from src.models.exam import Exam
    from src.models.question import Question


# Association table for the many-to-many between Question and Topic
question_topics = Table(
    "question_topics",
    Base.metadata,
    Column("question_id", Integer, ForeignKey("questions.id", ondelete="CASCADE"), primary_key=True),
    Column("topic_id", Integer, ForeignKey("topics.id", ondelete="CASCADE"), primary_key=True),
)


class Topic(Base):
    """A syllabus topic node in a three-level hierarchy.

    Hierarchy: Unit → Topic → Subtopic
    ``parent_id`` is NULL for top-level units.
    ``exam_id`` anchors the topic tree to a specific exam/course.
    """

    __tablename__ = "topics"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Self-referencing hierarchy (Unit > Topic > Subtopic)
    parent_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("topics.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # Depth for quick level detection (0 = unit, 1 = topic, 2 = subtopic)
    depth: Mapped[int] = mapped_column(default=0, nullable=False)

    # Foreign key - every topic belongs to an exam
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
    exam: Mapped["Exam"] = relationship("Exam", back_populates="topics")

    parent: Mapped[Optional["Topic"]] = relationship(
        "Topic", remote_side="Topic.id", back_populates="children"
    )
    children: Mapped[List["Topic"]] = relationship(
        "Topic", back_populates="parent", cascade="all, delete-orphan"
    )

    questions: Mapped[List["Question"]] = relationship(
        "Question", secondary=question_topics, back_populates="topics"
    )

    def __repr__(self) -> str:
        return f"<Topic id={self.id} name={self.name!r} depth={self.depth} exam_id={self.exam_id}>"
