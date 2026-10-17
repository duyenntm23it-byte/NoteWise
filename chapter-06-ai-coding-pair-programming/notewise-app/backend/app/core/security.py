from datetime import UTC, datetime, timedelta
from uuid import UUID

import bcrypt
import jwt

from app.core.config import settings


def hash_password(password: str) -> str:
    encoded_password = password.encode("utf-8")
    if len(encoded_password) > 72:
        raise ValueError("Passwords must be at most 72 UTF-8 bytes for bcrypt")
    return bcrypt.hashpw(encoded_password, bcrypt.gensalt()).decode("ascii")


def verify_password(password: str, hashed_password: str) -> bool:
    encoded_password = password.encode("utf-8")
    if len(encoded_password) > 72:
        return False
    try:
        return bcrypt.checkpw(encoded_password, hashed_password.encode("ascii"))
    except (ValueError, UnicodeEncodeError):
        return False


class JWTConfigurationError(RuntimeError):
    pass


def get_jwt_signing_key() -> str:
    key = settings.secret_key.get_secret_value()
    if len(key) < 32 or key.startswith("replace-with-"):
        raise JWTConfigurationError(
            "JWT authentication is unavailable: configure SECRET_KEY with a random value "
            "of at least 32 characters."
        )
    return key


def create_access_token(subject: UUID) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": str(subject),
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
    }
    return jwt.encode(payload, get_jwt_signing_key(), algorithm="HS256")


def decode_access_token(token: str) -> UUID:
    payload = jwt.decode(token, get_jwt_signing_key(), algorithms=["HS256"])
    subject = payload.get("sub")
    if not isinstance(subject, str):
        raise jwt.InvalidTokenError("Token subject is missing")
    try:
        return UUID(subject)
    except ValueError as exc:
        raise jwt.InvalidTokenError("Token subject is invalid") from exc
