import jwt
from fastapi import APIRouter, Depends, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import ApiError
from app.core.rate_limit import AuthRateLimiter
from app.core.security import get_token_subject
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import (
    AuthResponse,
    LoginRequest,
    RegisterRequest,
    UserResponse,
)
from app.schemas.errors import ErrorResponse
from app.services.auth import authenticate_user, load_user, register_user

router = APIRouter(prefix="/auth", tags=["Auth"])
bearer_scheme = HTTPBearer(
    auto_error=False,
    scheme_name="bearerAuth",
    bearerFormat="JWT",
)
auth_rate_limiter = AuthRateLimiter()


def enforce_auth_rate_limit(request: Request) -> None:
    operation = request.url.path.rsplit("/", maxsplit=1)[-1]
    limiter: AuthRateLimiter = getattr(
        request.app.state,
        "auth_rate_limiter",
        auth_rate_limiter,
    )
    limiter.check(operation, request.client.host if request.client else "unknown")


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise ApiError(401, "UNAUTHENTICATED", "Authentication is required.")
    try:
        user_id = get_token_subject(credentials.credentials)
    except (jwt.InvalidTokenError, ValueError, TypeError):
        raise ApiError(401, "UNAUTHENTICATED", "Invalid or expired access token.")

    user = load_user(db, user_id)
    if user is None:
        raise ApiError(401, "UNAUTHENTICATED", "Invalid or expired access token.")
    return user


@router.post(
    "/register",
    operation_id="register",
    status_code=status.HTTP_201_CREATED,
    response_model=AuthResponse,
    responses={
        409: {"model": ErrorResponse, "description": "Email already registered"},
        422: {"model": ErrorResponse, "description": "Request validation failed"},
        429: {"model": ErrorResponse, "description": "Authentication rate limit exceeded"},
    },
    dependencies=[Depends(enforce_auth_rate_limit)],
)
def register(
    payload: RegisterRequest,
    db: Session = Depends(get_db),
) -> AuthResponse:
    return register_user(
        db,
        payload.email,
        payload.password.get_secret_value(),
    )


@router.post(
    "/login",
    operation_id="login",
    response_model=AuthResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Invalid credentials"},
        422: {"model": ErrorResponse, "description": "Request validation failed"},
        429: {"model": ErrorResponse, "description": "Authentication rate limit exceeded"},
    },
    dependencies=[Depends(enforce_auth_rate_limit)],
)
def login(
    payload: LoginRequest,
    db: Session = Depends(get_db),
) -> AuthResponse:
    return authenticate_user(
        db,
        payload.email,
        payload.password.get_secret_value(),
    )


current_user_router = APIRouter(tags=["Auth"])


@current_user_router.get(
    "/me",
    operation_id="getCurrentUser",
    response_model=UserResponse,
    responses={401: {"model": ErrorResponse, "description": "Authentication required"}},
)
def get_current_user(
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    return UserResponse.model_validate(current_user)
