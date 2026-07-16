"""Unit and integration tests for Issue #4 – User auth, JWT, and exam/paper API."""

import pytest
from fastapi import Depends
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

from src.api.main import app
from src.api.middleware.auth import require_role
from src.database import get_db
from src.models import Base
from src.models.user import User, UserRole

# Create in-memory SQLite engine for auth API testing
engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})


@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_conn, _):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


# Add a client testing dummy route to verify role-based permissions
@app.get("/api/test-contributor")
def dummy_contributor_route(user: User = Depends(require_role(UserRole.CONTRIBUTOR))):
    return {"status": "ok", "user": user.email}


@pytest.fixture(scope="module")
def db():
    """Module-scoped database session."""
    Base.metadata.create_all(bind=engine)
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)

    yield session

    session.close()
    if transaction.is_active:
        transaction.rollback()
    connection.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="module")
def client(db):
    """FastAPI TestClient with overridden get_db dependency."""

    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ===========================================================================
# Test Cases
# ===========================================================================


def test_google_login_mock(client):
    """Test login flow via mock google OAuth code."""
    payload = {"code": "mock_code_john@example.com_John Doe_googleid123"}
    response = client.post("/api/auth/google", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "john@example.com"
    assert data["user"]["full_name"] == "John Doe"
    assert data["user"]["role"] == "student"  # default role


def test_jwt_validation_and_me(client):
    """Test that GET /api/users/me works with valid JWT."""
    # Obtain token first
    payload = {"code": "mock_code_validjwt@example.com_Valid User"}
    login_resp = client.post("/api/auth/google", json=payload)
    token = login_resp.json()["access_token"]

    # Request profile
    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/api/users/me", headers=headers)
    assert response.status_code == 200
    user_data = response.json()
    assert user_data["email"] == "validjwt@example.com"


def test_refresh_token_returns_a_new_valid_pair(client):
    login = client.post(
        "/api/auth/google",
        json={"code": "mock_code_refresh@example.com_Refresh User"},
    )
    response = client.post(
        "/api/auth/refresh",
        json={"refresh_token": login.json()["refresh_token"]},
    )
    assert response.status_code == 200
    assert response.json()["access_token"]
    assert response.json()["refresh_token"]

    profile = client.get(
        "/api/users/me",
        headers={"Authorization": f"Bearer {response.json()['access_token']}"},
    )
    assert profile.status_code == 200
    assert profile.json()["email"] == "refresh@example.com"


def test_protected_route_401(client):
    """Verify route triggers 401 when Authorization header is missing or invalid."""
    response = client.get("/api/users/me")
    assert response.status_code == 401

    headers = {"Authorization": "Bearer badtoken"}
    response = client.get("/api/users/me", headers=headers)
    assert response.status_code == 401


def test_role_check_permissions(client, db):
    """Verify role checks work for contributor role."""
    # 1. Create a student user
    student_payload = {"code": "mock_code_rolestudent@example.com_Student User"}
    student_token = client.post("/api/auth/google", json=student_payload).json()[
        "access_token"
    ]

    # Query route requiring contributor role -> should be 403 Forbidden
    resp = client.get(
        "/api/test-contributor", headers={"Authorization": f"Bearer {student_token}"}
    )
    assert resp.status_code == 403

    # 2. Add contributor user (we'll log in then elevate their role in testing DB)
    contributor_payload = {"code": "mock_code_rolecontrib@example.com_Contributor User"}
    client.post("/api/auth/google", json=contributor_payload)

    contrib_user = (
        db.query(User).filter(User.email == "rolecontrib@example.com").first()
    )
    contrib_user.role = UserRole.CONTRIBUTOR
    db.commit()

    # Re-login or use same token (email is same, matches decoded subject)
    contrib_token = client.post("/api/auth/google", json=contributor_payload).json()[
        "access_token"
    ]

    # Query route -> should be 200 OK
    resp = client.get(
        "/api/test-contributor", headers={"Authorization": f"Bearer {contrib_token}"}
    )
    assert resp.status_code == 200
    assert resp.json()["user"] == "rolecontrib@example.com"


def test_exam_crud(client, db):
    """Verify exam and paper CRUD APIs work and filters function correctly."""
    # Get auth token
    payload = {"code": "mock_code_examcrud@example.com_Exam Crud User"}
    token = client.post("/api/auth/google", json=payload).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    contributor = db.query(User).filter(User.email == "examcrud@example.com").first()
    contributor.role = UserRole.CONTRIBUTOR
    db.commit()

    # Create exam
    exam_payload = {
        "name": "GATE CS 2025",
        "exam_type": "gate",
        "year": 2025,
        "description": "GATE Computer Science 2025 exam",
    }
    response = client.post("/api/exams", json=exam_payload, headers=headers)
    assert response.status_code == 201
    exam_data = response.json()
    assert exam_data["id"] is not None
    assert exam_data["name"] == "GATE CS 2025"

    # Verify duplicate prevention code
    dup_resp = client.post("/api/exams", json=exam_payload, headers=headers)
    assert dup_resp.status_code == 400

    # Get exam papers list (initially empty)
    exams_resp = client.get("/api/exams", headers=headers)
    assert exams_resp.status_code == 200
    assert any(item["id"] == exam_data["id"] for item in exams_resp.json())

    detail_resp = client.get(f"/api/exams/{exam_data['id']}", headers=headers)
    assert detail_resp.status_code == 200
    assert detail_resp.json()["paper_count"] == 0

    papers_resp = client.get(f"/api/exams/{exam_data['id']}/papers", headers=headers)
    assert papers_resp.status_code == 200
    assert len(papers_resp.json()) == 0

    # Query papers directly
    all_papers_resp = client.get("/api/papers", headers=headers)
    assert all_papers_resp.status_code == 200

    # Query with filter
    filtered_resp = client.get("/api/papers?exam_type=gate&year=2025", headers=headers)
    assert filtered_resp.status_code == 200
    assert len(filtered_resp.json()) == 0
