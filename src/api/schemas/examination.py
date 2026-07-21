"""Pydantic schemas for Exams and Papers."""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field

from src.models.exam import ExamType


class ExamBase(BaseModel):
    name: str
    exam_type: ExamType = Field(validation_alias="type")
    year: int
    description: Optional[str] = None

    model_config = ConfigDict(populate_by_name=True)


class ExamCreate(ExamBase):
    pass


class ExamResponse(ExamBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ExamDetailResponse(ExamResponse):
    paper_count: int = 0


class PaperBase(BaseModel):
    pdf_path: str
    page_count: int
    original_filename: Optional[str] = None
    file_size_bytes: Optional[int] = None
    year: int
    session: Optional[str] = None
    total_marks: Optional[float] = None
    ocr_status: str = "pending"
    notes: Optional[str] = None
    exam_id: int


class PaperResponse(PaperBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PaperDetailResponse(PaperResponse):
    question_count: int = 0


class QuestionResponse(BaseModel):
    id: int
    paper_id: int
    text: str
    question_number: Optional[str] = None
    marks: Optional[float] = None
    question_type: Any
    year: Optional[int] = None
    image_path: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
