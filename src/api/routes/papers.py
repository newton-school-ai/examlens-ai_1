"""Exam and Paper management endpoints."""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from src.api.middleware.auth import get_current_user
from src.api.schemas.examination import ExamCreate, ExamResponse, PaperResponse
from src.database import get_db
from src.models.exam import Exam, ExamType
from src.models.paper import Paper
from src.models.user import User

router = APIRouter(prefix="", tags=["exams-papers"])


@router.post("/exams", response_model=ExamResponse, status_code=status.HTTP_201_CREATED)
def create_exam(
    exam_in: ExamCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new exam series under ExamLens."""
    existing = (
        db.query(Exam)
        .filter(Exam.name == exam_in.name, Exam.year == exam_in.year)
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Exam with this name and year already exists.",
        )
    # Convert ExamCreate to dict using model_dump in pydantic v2
    exam = Exam(**exam_in.model_dump())
    db.add(exam)
    db.commit()
    db.refresh(exam)
    return exam


@router.get("/exams/{id}/papers", response_model=List[PaperResponse])
def get_exam_papers(id: int, db: Session = Depends(get_db)):
    """List all papers belonging to a specific exam."""
    exam = db.query(Exam).filter(Exam.id == id).first()
    if not exam:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Exam not found.",
        )
    return exam.papers


@router.get("/papers", response_model=List[PaperResponse])
def get_papers(
    exam_type: Optional[str] = Query(
        None, description="Filter by exam type (e.g. gate, jee_mains)"
    ),
    year: Optional[int] = Query(None, description="Filter by year"),
    db: Session = Depends(get_db),
):
    """Filter and fetch papers by exam type and/or year."""
    query = db.query(Paper).join(Exam)
    if exam_type is not None:
        try:
            # Map standard inputs to lower
            e_type = ExamType(exam_type.lower())
            query = query.filter(Exam.exam_type == e_type)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid exam_type. Allowed types: {[t.value for t in ExamType]}",
            )
    if year is not None:
        query = query.filter(Exam.year == year)
    return query.all()
