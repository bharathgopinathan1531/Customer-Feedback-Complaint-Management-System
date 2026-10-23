import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.security import create_access_token, hash_password, verify_password
from app.db.session import get_db
from app.models.refresh_token import RefreshToken
from app.models.password_reset_token import PasswordResetToken
from app.models.user import User, UserRole
from app.schemas.auth import (
    PasswordResetConfirm,
    PasswordResetRequest,
    LoginRequest,
    RefreshTokenRequest,
    TokenResponse,
    UserRegister,
    UserResponse,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def issue_token_pair(db: Session, user: User) -> TokenResponse:
    raw_refresh_token = secrets.token_urlsafe(48)
    expires_at = datetime.now(timezone.utc) + timedelta(
        days=settings.refresh_token_expire_days
    )

    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=hash_refresh_token(raw_refresh_token),
            expires_at=expires_at,
        )
    )

    return TokenResponse(
        access_token=create_access_token(user.id),
        refresh_token=raw_refresh_token,
    )


def get_valid_refresh_record(
    db: Session,
    raw_token: str,
) -> RefreshToken:
    record = db.scalar(
        select(RefreshToken).where(
            RefreshToken.token_hash == hash_refresh_token(raw_token)
        )
    )

    if record is None or record.revoked_at is not None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or revoked refresh token",
        )

    expires_at = record.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if expires_at <= datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has expired",
        )

    user = db.get(User, record.user_id)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is unavailable",
        )

    return record


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(data: UserRegister, db: Session = Depends(get_db)):
    existing_user = db.scalar(
        select(User).where(User.email == data.email.lower())
    )
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        )

    user = User(
        full_name=data.full_name.strip(),
        email=data.email.lower(),
        hashed_password=hash_password(data.password),
        role=UserRole.CUSTOMER,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=TokenResponse)
def login(data: LoginRequest, db: Session = Depends(get_db)):
    user = db.scalar(
        select(User).where(User.email == data.email.lower())
    )

    if user is None or not verify_password(
        data.password, user.hashed_password
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account is deactivated",
        )

    tokens = issue_token_pair(db, user)
    db.commit()
    return tokens


@router.get("/me", response_model=UserResponse)
def read_current_user(
    current_user: User = Depends(get_current_user),
):
    return current_user


@router.post("/refresh", response_model=TokenResponse)
def refresh_tokens(
    data: RefreshTokenRequest,
    db: Session = Depends(get_db),
):
    record = get_valid_refresh_record(db, data.refresh_token)

    # Rotate the refresh token: the previous token cannot be reused.
    record.revoked_at = datetime.now(timezone.utc)
    user = db.get(User, record.user_id)
    tokens = issue_token_pair(db, user)

    db.commit()
    return tokens


@router.post("/logout")
def logout(
    data: RefreshTokenRequest,
    db: Session = Depends(get_db),
):
    record = get_valid_refresh_record(db, data.refresh_token)
    record.revoked_at = datetime.now(timezone.utc)
    db.commit()
    return {"message": "Logged out successfully"}


def hash_password_reset_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


@router.post("/password-reset/request")
def request_password_reset(
    data: PasswordResetRequest,
    db: Session = Depends(get_db),
):
    message = {
        "message": (
            "If an account exists for this email, "
            "password reset instructions have been generated."
        )
    }

    user = db.scalar(
        select(User).where(User.email == data.email.lower())
    )

    if user is None or not user.is_active:
        return message

    now = datetime.now(timezone.utc)

    old_tokens = db.scalars(
        select(PasswordResetToken).where(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.used_at.is_(None),
        )
    ).all()

    for old_token in old_tokens:
        old_token.used_at = now

    raw_token = secrets.token_urlsafe(32)
    reset_token = PasswordResetToken(
        user_id=user.id,
        token_hash=hash_password_reset_token(raw_token),
        expires_at=now + timedelta(
            minutes=settings.password_reset_expire_minutes
        ),
    )

    db.add(reset_token)
    db.commit()

    if settings.password_reset_expose_token:
        return {**message, "reset_token": raw_token}

    return message


@router.post("/password-reset/confirm")
def confirm_password_reset(
    data: PasswordResetConfirm,
    db: Session = Depends(get_db),
):
    token_record = db.scalar(
        select(PasswordResetToken).where(
            PasswordResetToken.token_hash
            == hash_password_reset_token(data.token)
        )
    )

    if token_record is None or token_record.used_at is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or already used password reset token",
        )

    expires_at = token_record.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if expires_at <= datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password reset token has expired",
        )

    user = db.get(User, token_record.user_id)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password reset is unavailable for this account",
        )

    user.hashed_password = hash_password(data.new_password)
    token_record.used_at = datetime.now(timezone.utc)

    # Revoke active refresh tokens after a password change.
    active_tokens = db.scalars(
        select(RefreshToken).where(
            RefreshToken.user_id == user.id,
            RefreshToken.revoked_at.is_(None),
        )
    ).all()

    for active_token in active_tokens:
        active_token.revoked_at = datetime.now(timezone.utc)

    db.commit()

    return {"message": "Password has been reset successfully"}
