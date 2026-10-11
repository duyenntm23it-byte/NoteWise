from datetime import datetime, timedelta, timezone
import uuid

import jwt
import pytest

from app.core.config import settings
from app.core.security import (
    create_access_token,
    get_token_subject,
    hash_password,
    verify_password,
)


def test_password_hash_verifies_original_without_storing_plaintext() -> None:
    password = "a-very-long-password-with-enough-entropy"
    password_hash = hash_password(password)

    assert password_hash != password
    assert password_hash.startswith("$bcrypt-sha256$")
    assert verify_password(password, password_hash)
    assert not verify_password("a-different-password", password_hash)


def test_access_token_contains_user_subject_and_expires_in_900_seconds() -> None:
    user_id = uuid.uuid4()
    token = create_access_token(user_id)

    claims = jwt.decode(
        token,
        settings.jwt_secret,
        algorithms=[settings.jwt_algorithm],
    )
    assert claims["sub"] == str(user_id)
    assert claims["exp"] - claims["iat"] == 900
    assert get_token_subject(token) == user_id


def test_expired_token_is_rejected() -> None:
    expired_token = jwt.encode(
        {
            "sub": str(uuid.uuid4()),
            "exp": datetime.now(timezone.utc) - timedelta(seconds=1),
        },
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )

    with pytest.raises(jwt.ExpiredSignatureError):
        get_token_subject(expired_token)


def test_token_signed_by_another_secret_is_rejected() -> None:
    token = jwt.encode(
        {
            "sub": str(uuid.uuid4()),
            "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
        },
        "not-the-configured-secret-which-is-over-thirty-two-bytes",
        algorithm=settings.jwt_algorithm,
    )

    with pytest.raises(jwt.InvalidSignatureError):
        get_token_subject(token)
