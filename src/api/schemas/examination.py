"""Pydantic schemas for Exams and Papers."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

from src.models.exam import ExamType


class ExamBase(BaseModel):
    name: str
    exam_type: ExamType
    year: int
    description: Optional[str] = None


class ExamCreate(ExamBase):
    pass


class ExamResponse(ExamBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PaperBase(BaseModel):
    pdf_path: str
    page_count: int
    original_filename: Optional[str] = None
    file_size_bytes: Optional[int] = None
    ocr_status: str = "pending"
    notes: Optional[str] = None
    exam_id: int


class PaperResponse(PaperBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
