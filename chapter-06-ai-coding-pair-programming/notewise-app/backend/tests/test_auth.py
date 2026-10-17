from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from pydantic import SecretStr
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.core.db import get_db_session
from app.main import app
from app.models.base import Base


@pytest_asyncio.fixture
async def client() -> AsyncIterator[AsyncClient]:
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as connection:
        users_table = Base.metadata.tables.get("users")
        assert users_table is not None, "The users table must be registered in model metadata"
        await connection.run_sync(users_table.create)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def override_db_session() -> AsyncIterator[AsyncSession]:
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db_session] = override_db_session
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
        ) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.pop(get_db_session, None)
        await engine.dispose()


@pytest.fixture(autouse=True)
def use_test_jwt_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "secret_key", SecretStr("test-only-secret-for-auth-tests-32"))


@pytest.mark.asyncio
async def test_register_and_get_current_profile(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": "Student@Example.com", "password": "correct-horse-123"},
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["token_type"] == "bearer"
    assert payload["user"]["email"] == "student@example.com"
    assert "password_hash" not in payload["user"]

    profile = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {payload['access_token']}"},
    )
    assert profile.status_code == 200
    assert profile.json() == payload["user"]


@pytest.mark.asyncio
async def test_login_returns_bearer_token(client: AsyncClient) -> None:
    await client.post(
        "/api/v1/auth/register",
        json={"email": "student@example.com", "password": "correct-horse-123"},
    )

    response = await client.post(
        "/api/v1/auth/token",
        data={"username": "student@example.com", "password": "correct-horse-123"},
    )

    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"
    assert response.json()["access_token"]


@pytest.mark.asyncio
async def test_register_rejects_duplicate_email_case_insensitively(
    client: AsyncClient,
) -> None:
    await client.post(
        "/api/v1/auth/register",
        json={"email": "student@example.com", "password": "correct-horse-123"},
    )

    response = await client.post(
        "/api/v1/auth/register",
        json={"email": "STUDENT@example.com", "password": "another-password-456"},
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "An account with this email already exists"


@pytest.mark.asyncio
async def test_login_rejects_wrong_password(client: AsyncClient) -> None:
    await client.post(
        "/api/v1/auth/register",
        json={"email": "student@example.com", "password": "correct-horse-123"},
    )

    response = await client.post(
        "/api/v1/auth/token",
        data={"username": "student@example.com", "password": "wrong-password-456"},
    )

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


@pytest.mark.asyncio
async def test_profile_requires_valid_bearer_token(client: AsyncClient) -> None:
    response = await client.get("/api/v1/auth/me")

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"

    invalid_token = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer not-a-valid-token"},
    )
    assert invalid_token.status_code == 401


@pytest.mark.asyncio
async def test_register_rejects_short_password(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": "student@example.com", "password": "short"},
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_register_rejects_passwords_over_bcrypt_byte_limit(
    client: AsyncClient,
) -> None:
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": "student@example.com", "password": "é" * 40},
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_register_fails_closed_when_jwt_secret_is_weak(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "secret_key", SecretStr("weak-key"))

    response = await client.post(
        "/api/v1/auth/register",
        json={"email": "student@example.com", "password": "correct-horse-123"},
    )

    assert response.status_code == 503
    assert response.json()["detail"].startswith("Authentication is not configured")
