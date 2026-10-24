import pytest
from fastapi.testclient import TestClient

from app.main import app, clock, tokens
from app.services.auth_service import AuthService
from tests.fakes import FakeHasher, FakeUnitOfWork, InMemoryDb


@pytest.fixture()
def client():
    """The real app and real JWTs, with an in-memory database behind the auth service."""
    db = InMemoryDb()
    real_service = app.state.auth_service
    app.state.auth_service = AuthService(lambda: FakeUnitOfWork(db), FakeHasher(), tokens, clock)
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


def test_login_returns_bearer_token(client):
    register(client)

    response = client.post("/auth/login", json={"username": "an_nguyen", "password": "matkhau123"})

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "Bearer"
    assert body["expires_in"] == 3600
    assert tokens.verify(body["access_token"]) == 1


@pytest.mark.parametrize("username, password", [("an_nguyen", "wrong-password"), ("nobody", "matkhau123")])
def test_login_wrong_credentials_look_the_same(client, username, password):
    register(client)

    response = client.post("/auth/login", json={"username": username, "password": password})

    assert response.status_code == 401
    assert response.json() == {"error": {"code": "INVALID_CREDENTIALS", "message": "Wrong username or password"}}


@pytest.mark.parametrize(
    "headers",
    [{}, {"Authorization": "Bearer not-a-jwt"}, {"Authorization": "Basic abc"}],
    ids=["missing", "invalid", "wrong-scheme"],
)
def test_route_needing_login_rejects_bad_token(client, headers):
    response = client.get("/wallet", headers=headers)

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


@pytest.mark.parametrize("method, path", [("POST", "/wallet/topups"), ("POST", "/auctions"), ("DELETE", "/auctions/1")])
def test_other_routes_needing_login_reject_missing_token(client, method, path):
    response = client.request(method, path)

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"
