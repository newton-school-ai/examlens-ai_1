"""SQLAlchemy models package.

Import all models here so that Alembic's env.py can discover them
via ``Base.metadata`` without needing to import each file individually.
"""

from src.models.base import Base  # noqa: F401
from src.models.exam import Exam, ExamType  # noqa: F401
from src.models.mock_test import MockTest  # noqa: F401
from src.models.paper import Paper  # noqa: F401
from src.models.question import Question, QuestionType  # noqa: F401
from src.models.solution import ConfidenceLevel, Solution  # noqa: F401
from src.models.study_plan import StudyPlan  # noqa: F401
from src.models.topic import Topic, question_topics  # noqa: F401
from src.models.user import User, UserRole  # noqa: F401

__all__ = [
    "Base",
    "ConfidenceLevel",
    "Exam",
    "ExamType",
    "MockTest",
    "Paper",
    "Question",
    "QuestionType",
    "question_topics",
    "Solution",
    "StudyPlan",
    "Topic",
    "User",
    "UserRole",
]
