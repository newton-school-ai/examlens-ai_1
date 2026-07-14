"""Exam and Paper management endpoints."""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from src.api.middleware.auth import get_current_user, require_role
from src.api.schemas.examination import (
    ExamCreate,
    ExamDetailResponse,
    ExamResponse,
    PaperDetailResponse,
    PaperResponse,
    QuestionResponse,
)
from src.database import get_db
from src.models.exam import Exam, ExamType
from src.models.paper import Paper
from src.models.user import User, UserRole

router = APIRouter(prefix="", tags=["exams-papers"])


@router.post("/exams", response_model=ExamResponse, status_code=status.HTTP_201_CREATED)
def create_exam(
    exam_in: ExamCreate,
    current_user: User = Depends(require_role(UserRole.CONTRIBUTOR)),
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


@router.get("/exams", response_model=List[ExamResponse])
def get_exams(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all configured examinations."""
    return db.query(Exam).order_by(Exam.name, Exam.year.desc()).all()


@router.get("/exams/{id}", response_model=ExamDetailResponse)
def get_exam(
    id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    exam = db.get(Exam, id)
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found.")
    result = ExamDetailResponse.model_validate(exam).model_dump()
    result["paper_count"] = len(exam.papers)
    return result


@router.get("/exams/{id}/papers", response_model=List[PaperResponse])
def get_exam_papers(
    id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
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
    exam_id: Optional[int] = Query(None),
    exam_type: Optional[str] = Query(None),
    year: Optional[int] = Query(None, description="Filter by year"),
    session: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Filter and fetch papers by exam type and/or year."""
    query = db.query(Paper).join(Exam)
    if exam_id is not None:
        query = query.filter(Paper.exam_id == exam_id)
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
        query = query.filter(Paper.year == year)
    if session is not None:
        query = query.filter(Paper.session == session)
    return query.all()


@router.get("/papers/{id}", response_model=PaperDetailResponse)
def get_paper(
    id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    paper = db.get(Paper, id)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found.")
    result = PaperDetailResponse.model_validate(paper).model_dump()
    result["question_count"] = len(paper.questions)
    return result


@router.get("/papers/{id}/questions", response_model=List[QuestionResponse])
def get_paper_questions(
    id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    paper = db.get(Paper, id)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found.")
    return paper.questions
