import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_db_ping
from app.main import app


@pytest.fixture()
def client():
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def database_is(up: bool) -> None:
    app.dependency_overrides[get_db_ping] = lambda: (lambda: up)


def test_health_ok_when_database_is_up(client):
    database_is(True)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "db": "up"}


def test_health_degraded_when_database_is_down(client):
    database_is(False)

    response = client.get("/health")

    assert response.status_code == 503
    assert response.json() == {"status": "degraded", "db": "down"}
