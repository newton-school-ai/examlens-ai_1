"""Authentication router for Google OAuth and session management."""

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.api.middleware.auth import (
    create_access_token,
    create_refresh_token,
    verify_token,
)
from src.api.schemas.user import GoogleAuthRequest, TokenResponse
from src.config.settings import settings
from src.database import get_db
from src.models.user import User, UserRole

router = APIRouter(prefix="/auth", tags=["auth"])


class RefreshTokenRequest(BaseModel):
    refresh_token: str


@router.post("/google", response_model=TokenResponse)
async def auth_google(request: GoogleAuthRequest, db: Session = Depends(get_db)):
    """Exchange a Google authorization code for JWT access and refresh tokens."""
    code = request.code
    email = None
    full_name = None
    avatar_url = None
    google_id = None

    if code.startswith("mock_code_"):
        # For unit testing and local development, support mock exchange
        # Format: mock_code_[email]_[full_name]_[google_id]
        parts = code.split("_")
        email = parts[2] if len(parts) > 2 else "mock@example.com"
        full_name = parts[3] if len(parts) > 3 else "Mock User"
        google_id = parts[4] if len(parts) > 4 else f"google_{email.split('@')[0]}"
        avatar_url = f"https://example.com/avatar/{email}.png"
    else:
        # Real Google code exchange
        async with httpx.AsyncClient() as client:
            token_url = "https://oauth2.googleapis.com/token"
            token_data = {
                "code": code,
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "redirect_uri": "postmessage",
                "grant_type": "authorization_code",
            }
            token_response = await client.post(token_url, data=token_data)
            if token_response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Google OAuth token exchange failed: {token_response.text}",
                )

            google_tokens = token_response.json()
            google_access_token = google_tokens.get("access_token")

            # Fetch user profile
            userinfo_url = "https://www.googleapis.com/oauth2/v3/userinfo"
            headers = {"Authorization": f"Bearer {google_access_token}"}
            userinfo_response = await client.get(userinfo_url, headers=headers)
            if userinfo_response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to retrieve Google user profile.",
                )

            user_info = userinfo_response.json()
            email = user_info.get("email")
            full_name = user_info.get("name")
            avatar_url = user_info.get("picture")
            google_id = user_info.get("sub")

    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google profile did not contain email address.",
        )

    # Find or auto-create user on first login
    user = db.query(User).filter(User.email == email).first()
    if not user:
        user = User(
            email=email,
            full_name=full_name,
            google_id=google_id,
            avatar_url=avatar_url,
            role=UserRole.STUDENT,
            auth_provider="google",
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    # Generate JWT tokens (24 hours access, 7 days refresh)
    access_token = create_access_token({"sub": user.email})
    refresh_token = create_refresh_token({"sub": user.email})

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": user,
    }


@router.post("/refresh", response_model=TokenResponse)
async def refresh(request: RefreshTokenRequest, db: Session = Depends(get_db)):
    """Refresh an expired access token using a valid refresh token."""
    payload = verify_token(request.refresh_token, "refresh")
    email = payload.get("sub")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token payload.",
        )

    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User associated with this token no longer exists.",
        )

    # Generate new pair of tokens
    access_token = create_access_token({"sub": user.email})
    refresh_token = create_refresh_token({"sub": user.email})

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": user,
    }


@router.post("/logout")
async def logout():
    """Stateless logout handler."""
    return {"status": "success", "message": "Logged out successfully."}
