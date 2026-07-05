"""Paper upload endpoints."""

import shutil
from pathlib import Path

from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from src.api.middleware.auth import get_current_user
from src.config.settings import settings
from src.database import get_db
from src.ingestion.image_handler import (
    SUPPORTED_IMAGE_EXTENSIONS,
    ImageValidationError,
)
from src.ingestion.page_extractor import (
    PageExtractionError,
    extract_pages_from_image,
    extract_pages_from_pdf,
)
from src.ingestion.pdf_handler import PDFValidationError
from src.models.paper import Paper
from src.models.user import User

router = APIRouter(prefix="/upload", tags=["upload"])

ALLOWED_EXTENSIONS = {".pdf"} | SUPPORTED_IMAGE_EXTENSIONS
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB


@router.post("", status_code=status.HTTP_201_CREATED)
async def upload_paper(
    file: UploadFile,
    exam_id: int = Form(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Upload a PDF or image file and extract individual pages.

    Accepts:
        - PDF files: each page rendered as a 300 DPI PNG.
        - Image files (JPG, PNG, etc.): stored as a single page.

    The file is validated (type, size, readability), stored in
    ``data/papers/{paper_id}/``, and a Paper record is created in the DB.
    """
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No filename provided.",
        )

    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type: {ext}. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )

    # Read file contents to validate size and check readability
    contents = await file.read()
    if len(contents) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Maximum size is {MAX_FILE_SIZE // (1024 * 1024)} MB.",
        )

    # Create a Paper record first so we have an ID for the storage path
    paper = Paper(
        pdf_path="",  # Will be updated after extraction
        page_count=0,
        original_filename=file.filename,
        file_size_bytes=len(contents),
        exam_id=exam_id,
    )
    db.add(paper)
    db.commit()
    db.refresh(paper)

    # Storage directory for this paper
    papers_dir = Path(settings.data_dir) / "papers" / str(paper.id)
    papers_dir.mkdir(parents=True, exist_ok=True)

    # Write uploaded file to disk
    temp_path = papers_dir / file.filename
    with open(temp_path, "wb") as f:
        f.write(contents)

    try:
        if ext == ".pdf":
            pages = extract_pages_from_pdf(temp_path, papers_dir, dpi=300)
            page_count = len(pages)
        else:
            pages = extract_pages_from_image(temp_path, papers_dir)
            page_count = len(pages)

        # Update paper record
        paper.pdf_path = str(papers_dir)
        paper.page_count = page_count
        paper.ocr_status = "pending"
        db.commit()
        db.refresh(paper)

    except (PDFValidationError, ImageValidationError, PageExtractionError) as exc:
        # Clean up on failure
        if papers_dir.exists():
            shutil.rmtree(papers_dir)
        db.delete(paper)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Failed to process uploaded file: {exc}",
        )

    return {
        "id": paper.id,
        "original_filename": paper.original_filename,
        "page_count": paper.page_count,
        "exam_id": paper.exam_id,
        "ocr_status": paper.ocr_status,
        "file_size_bytes": paper.file_size_bytes,
    }
