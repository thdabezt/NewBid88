import pytest
from fastapi.testclient import TestClient

from app.main import app, clock
from app.services.auth_service import AuthService
from tests.fakes import FakeHasher, FakeUnitOfWork, InMemoryDb


@pytest.fixture()
def client():
    """The real app, with an in-memory database behind the auth service."""
    db = InMemoryDb()
    real_service = app.state.auth_service
    app.state.auth_service = AuthService(lambda: FakeUnitOfWork(db), FakeHasher(), clock)
    with TestClient(app) as test_client:
        yield test_client
    app.state.auth_service = real_service


def register(client, username="an_nguyen", password="matkhau123"):
    return client.post("/auth/register", json={"username": username, "password": password})


def test_register_creates_account(client):
    response = register(client, username="An_Nguyen")

    assert response.status_code == 201
    body = response.json()
    assert body["username"] == "an_nguyen"
    assert set(body) == {"id", "username", "created_at"}
    assert body["created_at"].endswith("Z")


def test_register_taken_username(client):
    register(client)

    response = register(client)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "USERNAME_TAKEN"


@pytest.mark.parametrize(
    "username, password",
    [
        ("ab", "matkhau123"),  # username too short
        ("an nguyen", "matkhau123"),  # space not allowed
        ("an_nguyen", "short"),  # password under 8 characters
        ("an_nguyen", "ă" * 40),  # 40 characters but 80 bytes
    ],
)
def test_register_validates_input(client, username, password):
    response = register(client, username=username, password=password)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
