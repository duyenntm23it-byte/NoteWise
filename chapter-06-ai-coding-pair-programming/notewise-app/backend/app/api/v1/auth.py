from typing import Annotated

import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db import get_db_session
from app.core.security import (
    JWTConfigurationError,
    create_access_token,
    decode_access_token,
    get_jwt_signing_key,
)
from app.models.user import User
from app.schemas.auth import AuthToken, TokenOnly, UserPublic, UserRegister
from app.services.auth import (
    EmailAlreadyRegisteredError,
    authenticate_user,
    get_user_by_id,
    register_user,
)

router = APIRouter(prefix="/auth", tags=["authentication"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.api_v1_prefix}/auth/token")


def unavailable_authentication() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Authentication is not configured. Set a secure SECRET_KEY and restart the API.",
    )


@router.post("/register", response_model=AuthToken, status_code=status.HTTP_201_CREATED)
async def register(
    payload: UserRegister,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> AuthToken:
    try:
        get_jwt_signing_key()
    except JWTConfigurationError as exc:
        raise unavailable_authentication() from exc

    try:
        user = await register_user(session, str(payload.email), payload.password)
    except EmailAlreadyRegisteredError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        ) from exc

    return AuthToken(
        access_token=create_access_token(user.id),
        user=UserPublic.model_validate(user),
    )


@router.post("/token", response_model=TokenOnly)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> TokenOnly:
    try:
        get_jwt_signing_key()
    except JWTConfigurationError as exc:
        raise unavailable_authentication() from exc

    user = await authenticate_user(session, form_data.username, form_data.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return TokenOnly(access_token=create_access_token(user.id))


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> User:
    try:
        user_id = decode_access_token(token)
    except JWTConfigurationError as exc:
        raise unavailable_authentication() from exc
    except jwt.InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    user = await get_user_by_id(session, user_id)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


@router.get("/me", response_model=UserPublic)
async def profile(current_user: Annotated[User, Depends(get_current_user)]) -> UserPublic:
    return UserPublic.model_validate(current_user)
