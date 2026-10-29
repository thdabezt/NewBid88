import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.errors import register_error_handlers
from app.domain.errors import (
    AuthenticationError,
    ConflictError,
    DomainError,
    ForbiddenError,
    NotFoundError,
    ValidationError,
)
from app.main import app, tokens


def client_raising(exc: Exception) -> TestClient:
    test_app = FastAPI()
    register_error_handlers(test_app)

    @test_app.get("/boom")
    def boom():
        raise exc

    return TestClient(test_app, raise_server_exceptions=False)


@pytest.mark.parametrize(
    "exc, status",
    [
        (DomainError("INVALID_AMOUNT", "Amount out of range"), 400),
        (AuthenticationError("INVALID_CREDENTIALS", "Wrong username or password"), 401),
        (ForbiddenError("NOT_OWNER", "Not the seller"), 403),
        (NotFoundError("AUCTION_NOT_FOUND", "Auction not found"), 404),
        (ConflictError("AUCTION_HAS_BIDS", "Auction already has bids"), 409),
    ],
)
def test_domain_error_maps_to_status(exc, status):
    response = client_raising(exc).get("/boom")

    assert response.status_code == status
    assert response.json() == {"error": {"code": exc.code, "message": exc.message}}


def test_domain_error_keeps_details():
    exc = DomainError("BID_TOO_LOW", "Bid is below the minimum", {"min_required": 1150000})

    response = client_raising(exc).get("/boom")

    assert response.json()["error"]["details"] == {"min_required": 1150000}


def test_unexpected_error_hides_internals():
    response = client_raising(RuntimeError("secret stack info")).get("/boom")

    assert response.status_code == 500
    assert response.json() == {"error": {"code": "INTERNAL_ERROR", "message": "Unexpected server error"}}


def test_unknown_path_returns_not_found():
    token, _ = tokens.issue(1, "an_nguyen")

    response = TestClient(app).get("/no-such-path", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


def test_unknown_path_without_token_is_unauthorized():
    response = TestClient(app).get("/no-such-path")

    assert response.status_code == 401