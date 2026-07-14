"""Unit tests for Issue #3 – PDF/image upload API and page extraction pipeline.

Covers:
  1. PDF upload and page extraction
  2. Image upload and validation
  3. Invalid file rejection

Uses an in-memory SQLite database and tmpdir for file storage.

Run with:
    pytest tests/test_upload.py -v
"""

import io

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

from src.api.main import app
from src.database import get_db
from src.ingestion.image_handler import (
    ImageValidationError,
    get_image_info,
    save_image,
    validate_image,
)
from src.ingestion.page_extractor import (
    PageExtractionError,
    extract_pages_from_image,
    extract_pages_from_pdf,
)
from src.ingestion.pdf_handler import (
    PDFValidationError,
    extract_all_pages,
    extract_pdf_page_as_image,
    get_pdf_metadata,
    validate_pdf,
)
from src.models import Base
from src.models.user import User, UserRole

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def engine():
    eng = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})

    @event.listens_for(eng, "connect")
    def set_sqlite_pragma(dbapi_conn, _):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(bind=eng)
    yield eng
    Base.metadata.drop_all(bind=eng)


@pytest.fixture
def session(engine):
    connection = engine.connect()
    transaction = connection.begin()
    sess = Session(bind=connection)
    yield sess
    sess.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="module")
def db(engine):
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)
    yield session
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="module")
def client(db):
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def auth_token(client, db):
    """Obtain a valid JWT token via mock Google login."""
    payload = {"code": "mock_code_uploader@example.com_Uploader User_googleid"}
    resp = client.post("/api/auth/google", json=payload)
    user = db.query(User).filter(User.email == "uploader@example.com").first()
    user.role = UserRole.CONTRIBUTOR
    db.commit()
    return resp.json()["access_token"]


@pytest.fixture
def sample_pdf(tmp_path):
    """Create a minimal 2-page PDF for testing."""
    import fitz

    pdf_path = tmp_path / "test_paper.pdf"
    doc = fitz.open()
    page1 = doc.new_page(width=595, height=842)
    page1.insert_text((72, 72), "Page 1 content - Question 1")
    page2 = doc.new_page(width=595, height=842)
    page2.insert_text((72, 72), "Page 2 content - Question 2")
    doc.save(str(pdf_path))
    doc.close()
    return pdf_path


@pytest.fixture
def sample_image(tmp_path):
    """Create a valid test image (800x600 PNG)."""
    img_path = tmp_path / "test_image.png"
    img = Image.new("RGB", (800, 600), color=(255, 255, 255))
    img.save(str(img_path))
    return img_path


@pytest.fixture
def small_image(tmp_path):
    """Create an image below minimum resolution (320x240)."""
    img_path = tmp_path / "small_image.png"
    img = Image.new("RGB", (320, 240), color=(255, 255, 255))
    img.save(str(img_path))
    return img_path


# ===========================================================================
# 1. PDF handler unit tests
# ===========================================================================


class TestPDFHandler:
    """Test PDF validation, metadata, and page extraction."""

    def test_validate_pdf_succeeds(self, sample_pdf):
        validate_pdf(sample_pdf)

    def test_validate_pdf_not_found(self):
        with pytest.raises(PDFValidationError, match="File not found"):
            validate_pdf("/nonexistent/file.pdf")

    def test_validate_pdf_empty_file(self, tmp_path):
        empty = tmp_path / "empty.pdf"
        empty.touch()
        with pytest.raises(PDFValidationError, match="File is empty"):
            validate_pdf(empty)

    def test_validate_pdf_corrupted(self, tmp_path):
        bad = tmp_path / "bad.pdf"
        bad.write_bytes(b"not a pdf at all")
        with pytest.raises(PDFValidationError, match="Invalid PDF"):
            validate_pdf(bad)

    def test_get_pdf_metadata(self, sample_pdf):
        meta = get_pdf_metadata(sample_pdf)
        assert meta["page_count"] == 2
        assert meta["file_size_bytes"] > 0

    def test_extract_all_pages(self, sample_pdf, tmp_path):
        pages = extract_all_pages(sample_pdf, tmp_path / "out", dpi=72)
        assert len(pages) == 2
        for p in pages:
            assert p.exists()
            assert p.suffix == ".png"

    def test_extract_single_page(self, sample_pdf, tmp_path):
        out = tmp_path / "single.png"
        result = extract_pdf_page_as_image(sample_pdf, 0, out, dpi=72)
        assert result.exists()

    def test_extract_page_out_of_range(self, sample_pdf, tmp_path):
        with pytest.raises(PDFValidationError, match="out of range"):
            extract_pdf_page_as_image(sample_pdf, 99, tmp_path / "x.png")


# ===========================================================================
# 2. Image handler unit tests
# ===========================================================================


class TestImageHandler:
    """Test image validation, info, and saving."""

    def test_validate_image_succeeds(self, sample_image):
        validate_image(sample_image)

    def test_validate_image_too_small(self, small_image):
        with pytest.raises(ImageValidationError, match="too small"):
            validate_image(small_image)

    def test_validate_image_not_found(self):
        with pytest.raises(ImageValidationError, match="File not found"):
            validate_image("/nonexistent/photo.jpg")

    def test_validate_image_empty(self, tmp_path):
        empty = tmp_path / "empty.png"
        empty.touch()
        with pytest.raises(ImageValidationError, match="File is empty"):
            validate_image(empty)

    def test_validate_image_bad_extension(self, tmp_path):
        bad = tmp_path / "file.xyz"
        bad.write_bytes(b"not an image")
        with pytest.raises(ImageValidationError, match="Unsupported image format"):
            validate_image(bad)

    def test_get_image_info(self, sample_image):
        info = get_image_info(sample_image)
        assert info["width"] == 800
        assert info["height"] == 600
        assert info["file_size_bytes"] > 0

    def test_save_image(self, sample_image, tmp_path):
        dest = tmp_path / "saved.png"
        result = save_image(sample_image, dest)
        assert result.exists()
        saved = Image.open(result)
        assert saved.size == (800, 600)
        saved.close()


# ===========================================================================
# 3. Page extractor unit tests
# ===========================================================================


class TestPageExtractor:
    """Test PDF and image page extraction."""

    def test_extract_pages_from_pdf(self, sample_pdf, tmp_path):
        pages = extract_pages_from_pdf(sample_pdf, tmp_path / "pages")
        assert len(pages) == 2

    def test_extract_pages_from_pdf_invalid(self, tmp_path):
        bad = tmp_path / "bad.pdf"
        bad.write_bytes(b"not pdf")
        with pytest.raises(PageExtractionError):
            extract_pages_from_pdf(bad, tmp_path / "out")

    def test_extract_pages_from_image(self, sample_image, tmp_path):
        pages = extract_pages_from_image(sample_image, tmp_path / "img_pages")
        assert len(pages) == 1
        assert pages[0].exists()

    def test_extract_pages_from_image_invalid(self, small_image, tmp_path):
        with pytest.raises(PageExtractionError, match="too small"):
            extract_pages_from_image(small_image, tmp_path / "out")


# ===========================================================================
# 4. Upload API integration tests
# ===========================================================================


class TestUploadAPI:
    """Test the POST /api/upload endpoint."""

    def _make_pdf_bytes(self, text="Test upload content"):
        """Create an in-memory PDF for upload."""
        import fitz

        buf = io.BytesIO()
        doc = fitz.open()
        page = doc.new_page(width=595, height=842)
        page.insert_text((72, 72), text)
        doc.save(buf)
        doc.close()
        buf.seek(0)
        return buf.getvalue()

    def _make_image_bytes(self):
        """Create an in-memory PNG for upload."""
        img = Image.new("RGB", (800, 600), color=(255, 255, 255))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        return buf.getvalue()

    _exam_counter = 0

    def _get_exam_id(self, client, token):
        """Create an exam and return its ID. Uses unique names per test."""
        TestUploadAPI._exam_counter += 1
        headers = {"Authorization": f"Bearer {token}"}
        resp = client.post(
            "/api/exams",
            json={
                "name": f"Upload Test Exam {TestUploadAPI._exam_counter}",
                "exam_type": "gate",
                "year": 2025,
            },
            headers=headers,
        )
        assert resp.status_code == 201, f"Exam creation failed: {resp.json()}"
        return resp.json()["id"]

    def test_upload_pdf_success(self, client, auth_token):
        exam_id = self._get_exam_id(client, auth_token)
        headers = {"Authorization": f"Bearer {auth_token}"}
        pdf_bytes = self._make_pdf_bytes()

        response = client.post(
            "/api/upload",
            files={"file": ("test.pdf", pdf_bytes, "application/pdf")},
            data={"exam_id": exam_id, "year": 2025, "session": "Morning"},
            headers=headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["page_count"] >= 1
        assert data["original_filename"] == "test.pdf"
        assert data["exam_id"] == exam_id
        assert data["ocr_status"] == "pending"
        assert data["year"] == 2025
        assert len(data["pages"]) == data["page_count"]
        assert data["pages"][0]["page_num"] == 1

        detail = client.get(f"/api/papers/{data['paper_id']}", headers=headers)
        assert detail.status_code == 200
        assert detail.json()["question_count"] == 0
        questions = client.get(
            f"/api/papers/{data['paper_id']}/questions", headers=headers
        )
        assert questions.status_code == 200
        assert questions.json() == []

    def test_upload_image_success(self, client, auth_token):
        exam_id = self._get_exam_id(client, auth_token)
        headers = {"Authorization": f"Bearer {auth_token}"}
        img_bytes = self._make_image_bytes()

        response = client.post(
            "/api/upload",
            files={"file": ("photo.png", img_bytes, "image/png")},
            data={"exam_id": exam_id, "year": 2025},
            headers=headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["page_count"] == 1
        assert data["original_filename"] == "photo.png"

    def test_upload_rejects_unsupported_type(self, client, auth_token):
        exam_id = self._get_exam_id(client, auth_token)
        headers = {"Authorization": f"Bearer {auth_token}"}

        response = client.post(
            "/api/upload",
            files={"file": ("doc.txt", b"hello world", "text/plain")},
            data={"exam_id": exam_id, "year": 2025},
            headers=headers,
        )
        assert response.status_code == 400
        assert "Unsupported file type" in response.json()["detail"]

    def test_upload_rejects_empty_file(self, client, auth_token):
        exam_id = self._get_exam_id(client, auth_token)
        headers = {"Authorization": f"Bearer {auth_token}"}

        response = client.post(
            "/api/upload",
            files={"file": ("empty.pdf", b"", "application/pdf")},
            data={"exam_id": exam_id, "year": 2025},
            headers=headers,
        )
        assert response.status_code == 400

    def test_upload_rejects_large_file(self, client, auth_token):
        exam_id = self._get_exam_id(client, auth_token)
        headers = {"Authorization": f"Bearer {auth_token}"}

        # 51 MB file
        large = b"x" * (51 * 1024 * 1024)
        response = client.post(
            "/api/upload",
            files={"file": ("big.pdf", large, "application/pdf")},
            data={"exam_id": exam_id, "year": 2025},
            headers=headers,
        )
        assert response.status_code == 400
        assert "too large" in response.json()["detail"].lower()

    def test_upload_requires_auth(self, client):
        response = client.post(
            "/api/upload",
            files={"file": ("test.pdf", b"not pdf", "application/pdf")},
            data={"exam_id": 1, "year": 2025},
        )
        assert response.status_code == 401

    def test_upload_rejects_corrupted_pdf(self, client, auth_token):
        exam_id = self._get_exam_id(client, auth_token)
        headers = {"Authorization": f"Bearer {auth_token}"}

        response = client.post(
            "/api/upload",
            files={"file": ("corrupt.pdf", b"not a real pdf", "application/pdf")},
            data={"exam_id": exam_id, "year": 2025},
            headers=headers,
        )
        assert response.status_code == 422

    def test_upload_rejects_duplicate_file(self, client, auth_token):
        exam_id = self._get_exam_id(client, auth_token)
        headers = {"Authorization": f"Bearer {auth_token}"}
        payload = self._make_pdf_bytes("Unique duplicate-detection content")
        form = {"exam_id": exam_id, "year": 2025}
        first = client.post(
            "/api/upload",
            files={"file": ("unique-duplicate-test.pdf", payload, "application/pdf")},
            data=form,
            headers=headers,
        )
        assert first.status_code == 201
        second = client.post(
            "/api/upload",
            files={"file": ("same-content.pdf", payload, "application/pdf")},
            data=form,
            headers=headers,
        )
        assert second.status_code == 409

    def test_upload_requires_contributor_role(self, client):
        login = client.post(
            "/api/auth/google",
            json={"code": "mock_code_student-upload@example.com_Student User"},
        )
        token = login.json()["access_token"]
        response = client.post(
            "/api/upload",
            files={"file": ("paper.pdf", b"not important", "application/pdf")},
            data={"exam_id": 1, "year": 2025},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403
