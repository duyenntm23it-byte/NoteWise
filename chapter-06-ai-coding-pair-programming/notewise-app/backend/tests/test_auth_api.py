from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.rate_limit import AuthRateLimiter
from app.db.session import Base, get_db
from app.main import app
from app.models.user import User


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
    )
    Base.metadata.create_all(engine)
    app.state.testing_session_factory = TestingSessionLocal
    app.state.disable_document_worker = True
    app.state.auth_rate_limiter = AuthRateLimiter()

    def override_get_db() -> Generator[Session, None, None]:
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    for state_key in (
        "testing_session_factory",
        "disable_document_worker",
        "auth_rate_limiter",
    ):
        if hasattr(app.state, state_key):
            delattr(app.state, state_key)
    Base.metadata.drop_all(engine)
    engine.dispose()


def register_user(client: TestClient, email: str = "student@example.com") -> dict:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "secure-password-123"},
    )
    assert response.status_code == 201
    return response.json()


def test_register_returns_contract_and_stores_only_password_hash(
    client: TestClient,
) -> None:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "Student@example.com", "password": "secure-password-123"},
    )

    assert response.status_code == 201
    payload = response.json()
    assert set(payload) == {"access_token", "token_type", "expires_in", "user"}
    assert payload["token_type"] == "Bearer"
    assert payload["expires_in"] == 900
    assert set(payload["user"]) == {"id", "email", "created_at"}
    assert payload["user"]["email"] == "student@example.com"
    assert payload["access_token"]

    with app.state.testing_session_factory() as db:
        user = db.query(User).one()
        assert user.password_hash != "secure-password-123"
        assert user.password_hash.startswith("$bcrypt-sha256$")


@pytest.mark.parametrize(
    ("payload", "field"),
    [
        ({}, "email"),
        ({"email": "not-an-email", "password": "secure-password-123"}, "email"),
        ({"email": "student@example.com", "password": "short"}, "password"),
        (
            {"email": "student@example.com", "password": "p" * 129},
            "password",
        ),
        (
            {
                "email": "student@example.com",
                "password": "secure-password-123",
                "user_id": "attacker-controlled",
            },
            "user_id",
        ),
    ],
)
def test_register_rejects_invalid_credentials_without_creating_user(
    client: TestClient,
    payload: dict,
    field: str,
) -> None:
    response = client.post("/api/v1/auth/register", json=payload)

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "VALIDATION_ERROR"
    assert error["request_id"]
    assert field in str(error.get("details", {}))
    with app.state.testing_session_factory() as db:
        assert db.query(User).count() == 0


def test_register_rejects_duplicate_email_without_disclosing_identity(
    client: TestClient,
) -> None:
    register_user(client)

    response = client.post(
        "/api/v1/auth/register",
        json={"email": "STUDENT@example.com", "password": "other-password-123"},
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "STATE_CONFLICT"


def test_login_returns_token_and_me_uses_verified_token_subject(
    client: TestClient,
) -> None:
    registered = register_user(client)

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "student@example.com", "password": "secure-password-123"},
    )

    assert response.status_code == 200
    login_payload = response.json()
    assert login_payload["token_type"] == "Bearer"
    assert login_payload["expires_in"] == 900
    assert login_payload["user"]["id"] == registered["user"]["id"]
    assert "password" not in response.text
    assert "$bcrypt" not in response.text

    me = client.get(
        "/api/v1/me",
        headers={"Authorization": f"Bearer {login_payload['access_token']}"},
        params={"user_id": "another-user"},
    )
    assert me.status_code == 200
    assert me.json() == registered["user"]


def test_users_can_only_resolve_their_own_profile_from_their_token(
    client: TestClient,
) -> None:
    first_user = register_user(client, "first@example.com")
    register_user(client, "second@example.com")

    response = client.get(
        "/api/v1/me",
        headers={"Authorization": f"Bearer {first_user['access_token']}"},
    )

    assert response.status_code == 200
    assert response.json() == first_user["user"]


@pytest.mark.parametrize(
    "email",
    ["student@example.com", "missing@example.com"],
)
def test_login_rejects_bad_password_or_unknown_user_generically(
    client: TestClient,
    email: str,
) -> None:
    register_user(client)

    response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "incorrect-password"},
    )

    assert response.status_code == 401
    error = response.json()["error"]
    assert error["code"] == "UNAUTHENTICATED"
    assert error["message"] == "Invalid email or password."


@pytest.mark.parametrize(
    "authorization",
    [None, "Basic not-a-bearer", "Bearer malformed.token"],
)
def test_me_requires_valid_bearer_token(
    client: TestClient,
    authorization: str | None,
) -> None:
    headers = {"Authorization": authorization} if authorization else {}

    response = client.get("/api/v1/me", headers=headers)

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHENTICATED"
    assert response.json()["error"]["request_id"]


def test_registration_password_limit_uses_utf8_byte_safe_hasher(
    client: TestClient,
) -> None:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "long@example.com", "password": "é" * 64},
    )

    assert response.status_code == 201
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "long@example.com", "password": "é" * 64},
    )
    assert login.status_code == 200


def test_registration_accepts_contract_maximum_password_length(
    client: TestClient,
) -> None:
    password = "p" * 128
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "maximum@example.com", "password": password},
    )

    assert response.status_code == 201
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "maximum@example.com", "password": password},
    )
    assert login.status_code == 200


def test_auth_routes_match_approved_openapi_contract() -> None:
    schema = app.openapi()
    paths = schema["paths"]
    assert {
        "/api/v1/auth/register",
        "/api/v1/auth/login",
        "/api/v1/me",
    }.issubset(paths)
    assert paths["/api/v1/auth/register"]["post"]["operationId"] == "register"
    assert paths["/api/v1/auth/login"]["post"]["operationId"] == "login"
    assert paths["/api/v1/me"]["get"]["operationId"] == "getCurrentUser"
    assert "bearerAuth" in schema["components"]["securitySchemes"]
    register_operation = paths["/api/v1/auth/register"]["post"]
    register_schema_ref = register_operation["requestBody"]["content"][
        "application/json"
    ]["schema"]["$ref"]
    register_schema_name = register_schema_ref.rsplit("/", maxsplit=1)[-1]
    register_properties = schema["components"]["schemas"][register_schema_name][
        "properties"
    ]
    assert set(register_properties) == {"email", "password"}
    assert register_properties["password"]["minLength"] == 12
    assert register_properties["password"]["maxLength"] == 128
    assert schema["components"]["schemas"][register_schema_name][
        "additionalProperties"
    ] is False
    assert {"201", "409", "422", "429"}.issubset(
        register_operation["responses"]
    )
    assert register_operation["responses"]["422"]["content"][
        "application/json"
    ]["schema"] == {"$ref": "#/components/schemas/ErrorResponse"}
    login_operation = paths["/api/v1/auth/login"]["post"]
    assert {"200", "401", "422", "429"}.issubset(login_operation["responses"])
    assert login_operation["responses"]["401"]["content"][
        "application/json"
    ]["schema"] == {"$ref": "#/components/schemas/ErrorResponse"}
    assert {"200", "401"}.issubset(paths["/api/v1/me"]["get"]["responses"])
    assert paths["/api/v1/me"]["get"]["security"] == [{"bearerAuth": []}]
    components = schema["components"]["schemas"]
    assert schema["components"]["securitySchemes"]["bearerAuth"] == {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "JWT",
    }
    auth_response = components["AuthResponse"]
    user_schema_ref = auth_response["properties"]["user"]["$ref"]
    user_schema_name = user_schema_ref.rsplit("/", maxsplit=1)[-1]
    user_schema = components[user_schema_name]
    assert components["AuthResponse"]["properties"]["token_type"]["const"] == "Bearer"
    assert components["AuthResponse"]["properties"]["expires_in"]["const"] == 900
    assert {"access_token", "token_type", "expires_in", "user"} == set(
        auth_response["required"]
    )
    assert {"id", "email", "created_at"} == set(user_schema["properties"])
    assert paths["/api/v1/me"]["get"]["responses"]["200"]["content"][
        "application/json"
    ]["schema"] == {"$ref": user_schema_ref}
    assert components["ErrorResponse"]["properties"]["error"]["$ref"] == (
        "#/components/schemas/ErrorDetail"
    )


def test_auth_endpoints_return_contract_rate_limit_error(
    client: TestClient,
) -> None:
    client.app.state.auth_rate_limiter = AuthRateLimiter(
        register_limit=0,
        login_limit=0,
    )

    response = client.post(
        "/api/v1/auth/register",
        json={"email": "student@example.com", "password": "secure-password-123"},
    )

    assert response.status_code == 429
    assert response.json()["error"]["code"] == "RATE_LIMITED"
