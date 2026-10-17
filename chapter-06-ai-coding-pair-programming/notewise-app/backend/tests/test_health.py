from fastapi.testclient import TestClient

from app.main import app


def test_root_returns_health_status() -> None:
    with TestClient(app) as client:
        response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "docs": "/docs"}


def test_cors_allows_local_frontend() -> None:
    with TestClient(app) as client:
        response = client.options(
            "/",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
