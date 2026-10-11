import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import ApiError
from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User
from app.schemas.auth import AuthResponse, UserResponse


def normalize_email(email: str) -> str:
    return email.strip().casefold()


def _auth_response(user: User) -> AuthResponse:
    return AuthResponse(
        access_token=create_access_token(user.id),
        token_type="Bearer",
        expires_in=settings.access_token_expire_seconds,
        user=UserResponse.model_validate(user),
    )


def register_user(db: Session, email: str, password: str) -> AuthResponse:
    normalized_email = normalize_email(email)
    existing_user = db.scalar(select(User).where(User.email == normalized_email))
    if existing_user:
        raise ApiError(
            409,
            "STATE_CONFLICT",
            "An account with this email already exists.",
        )

    user = User(
        email=normalized_email,
        password_hash=hash_password(password),
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ApiError(
            409,
            "STATE_CONFLICT",
            "An account with this email already exists.",
        ) from exc
    db.refresh(user)
    return _auth_response(user)


def authenticate_user(db: Session, email: str, password: str) -> AuthResponse:
    user = db.scalar(
        select(User).where(User.email == normalize_email(email))
    )
    if user is None or not verify_password(password, user.password_hash):
        raise ApiError(
            401,
            "UNAUTHENTICATED",
            "Invalid email or password.",
        )
    return _auth_response(user)


def load_user(db: Session, user_id: uuid.UUID) -> User | None:
    return db.get(User, user_id)
