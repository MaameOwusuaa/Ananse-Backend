"""Registration and sign in."""

import secrets

from fastapi import APIRouter, Depends, HTTPException, status
from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2 import id_token
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.security import create_access_token, hash_password, verify_password
from app.deps import current_user
from app.models import User
from app.schemas import GoogleLoginIn, LoginIn, RegisterIn, TokenOut, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenOut, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterIn, db: Session = Depends(get_db)) -> TokenOut:
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account already uses that email address",
        )

    user = User(
        full_name=payload.full_name.strip(),
        email=payload.email.lower(),
        password_hash=hash_password(payload.password),
        role="visitor",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return TokenOut(access_token=create_access_token(user.email), user=UserOut.model_validate(user))


@router.post("/login", response_model=TokenOut)
def login(payload: LoginIn, db: Session = Depends(get_db)) -> TokenOut:
    user = db.query(User).filter(User.email == payload.email.lower()).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="That email and password do not match an account",
        )

    return TokenOut(access_token=create_access_token(user.email), user=UserOut.model_validate(user))


@router.post("/google", response_model=TokenOut)
def google_login(payload: GoogleLoginIn, db: Session = Depends(get_db)) -> TokenOut:
    if not settings.google_client_id:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google sign-in is not configured",
        )

    try:
        claims = id_token.verify_oauth2_token(
            payload.id_token,
            GoogleRequest(),
            settings.google_client_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Google credential is invalid or expired",
        ) from exc

    email = claims.get("email")
    if not isinstance(email, str) or claims.get("email_verified") is not True:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Google account does not have a verified email address",
        )

    normalized_email = email.lower()
    user = db.query(User).filter(User.email == normalized_email).first()
    if not user:
        full_name = claims.get("name")
        user = User(
            full_name=full_name.strip() if isinstance(full_name, str) and full_name.strip() else normalized_email,
            email=normalized_email,
            password_hash=hash_password(secrets.token_urlsafe(32)),
            role="visitor",
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    return TokenOut(access_token=create_access_token(user.email), user=UserOut.model_validate(user))


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(current_user)) -> User:
    return user
