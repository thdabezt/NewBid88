import pytest
from fastapi.testclient import TestClient

from app.main import app, clock, tokens
from app.services.auth_service import AuthService
from tests.fakes import FakeHasher, FakeUnitOfWork, InMemoryDb


@pytest.fixture()
def client():
    db = InMemoryDb()
    real_service = app.state.auth_service
    app.state.auth_service = AuthService(lambda: FakeUnitOfWork(db), FakeHasher(), tokens, clock)
    with TestClient(app) as test_client:
        yield test_client
    app.state.auth_service = real_service


def register(client, username="an_nguyen", password="matkhau123"):
    return client.post("/auth/register", json={"username": username, "password": password})


def login_header(client, username="an_nguyen", password="matkhau123") -> dict[str, str]:
    token = client.post("/auth/login", json={"username": username, "password": password}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


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
        ("ab", "matkhau123"),
        ("an nguyen", "matkhau123"),
        ("an_nguyen", "short"),
        ("an_nguyen", "ă" * 40),
    ],
    ids=["username-too-short", "username-with-space", "password-too-short", "password-over-72-bytes"],
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


@pytest.mark.parametrize("method, path", [("GET", "/wallet"), ("POST", "/auctions/1/bids"), ("GET", "/users/me/bids")])

@pytest.mark.parametrize(
    "headers",
    [{}, {"Authorization": "Bearer not-a-jwt"}, {"Authorization": "Basic abc"}],
    ids=["missing", "invalid", "wrong-scheme"],
)
def test_route_needing_login_rejects_bad_token(client, headers, method, path):
    response = client.request(method, path, headers=headers)

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


@pytest.mark.parametrize("method, path", [
    ("POST", "/wallet/topups"), ("POST", "/auctions"), ("DELETE", "/auctions/1"),
    ("POST", "/auctions/1/bids"), ("GET", "/users/me/bids"),
])
def test_other_routes_needing_login_reject_missing_token(client, method, path):
    response = client.request(method, path)

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


def test_me_returns_logged_in_user(client):
    user = register(client).json()

    response = client.get("/users/me", headers=login_header(client))

    assert response.status_code == 200
    assert response.json() == user


def test_me_needs_login(client):
    response = client.get("/users/me")

    assert response.status_code == 401


def test_me_when_user_no_longer_exists(client):
    token, _ = tokens.issue(999, "ghost")

    response = client.get("/users/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "USER_NOT_FOUND"


def test_swagger_is_public_and_lists_auth_endpoints(client):
    assert client.get("/docs").status_code == 200

    spec = client.get("/openapi.json").json()

    assert {"/auth/register", "/auth/login", "/users/me"} <= set(spec["paths"])
    assert spec["paths"]["/users/me"]["get"]["security"] == [{"HTTPBearer": []}]
    assert spec["paths"]["/auctions/{id}/bids"]["post"]["security"] == [{"HTTPBearer": []}]
    assert spec["paths"]["/users/me/bids"]["get"]["security"] == [{"HTTPBearer": []}]
    assert not spec["paths"]["/auctions/{id}/bids"]["get"].get("security")