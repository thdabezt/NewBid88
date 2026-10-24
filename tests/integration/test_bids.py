from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.main import app, tokens
from tests.fakes import FakeBidsUnitOfWork


@pytest.fixture()

def client(bids_db, monkeypatch):
    monkeypatch.setattr(app.state, "uow_factory", lambda: FakeBidsUnitOfWork(bids_db))
    with TestClient(app) as test_client:
        yield test_client


def auth_header(user_id=2):
    token, _ = tokens.issue(user_id, f"user_{user_id}")
    return {"Authorization": f"Bearer {token}"}


# API #8
def test_place_bid_returns_201_and_uses_token_user(client, bids_db):
    response = client.post("/auctions/1/bids", headers=auth_header(), json={"amount": 20_000, "bidder_id": 3})
    assert response.status_code == 201
    body = response.json()
    assert set(body) == {"bid", "auction", "wallet"}
    assert body["bid"]["auction_id"] == 1
    assert body["bid"]["amount"] == 20_000
    assert body["bid"]["created_at"].endswith("Z")
    assert body["auction"]["current_price"] == 20_000
    assert body["auction"]["bid_count"] == 1
    assert body["wallet"] == {"balance": 100_000, "held": 20_000, "available": 80_000}
    assert bids_db.bids[0].bidder_id == 2


@pytest.mark.parametrize("body", [{}, {"amount": "20000"}, {"amount": 20_000.5}, {"amount": True}])

def test_place_bid_invalid_body(client, body):
    response = client.post("/auctions/1/bids", headers=auth_header(), json=body)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.parametrize("case, status, code, details", [
    ("missing", 404, "AUCTION_NOT_FOUND", None),
    ("seller", 403, "SELLER_CANNOT_BID", None),
    ("closed", 409, "AUCTION_NOT_ACTIVE", None),
    ("low", 400, "BID_TOO_LOW", {"min_required": 20_000}),
    ("funds", 400, "INSUFFICIENT_FUNDS", {"available": 10_000}),
])

def test_place_bid_business_error_response(client, bids_db, case, status, code, details):
    if case == "closed":
        bids_db.auctions[1].status = "SOLD"
    if case == "funds":
        bids_db.wallets[2].held = 90_000
    auction_id = 999 if case == "missing" else 1
    user_id = 1 if case == "seller" else 2
    amount = 19_000 if case == "low" else 20_000
    response = client.post(f"/auctions/{auction_id}/bids", headers=auth_header(user_id),
                           json={"amount": amount})
    assert response.status_code == status
    error = response.json()["error"]
    assert error["code"] == code
    if details is not None:
        assert error["details"] == details


# API #9
def test_history_is_public_and_masks_username(client, bids_db, bids_now):
    bids_db.history_rows = [(SimpleNamespace(id=7, amount=25_000, created_at=bids_now), "binh_nguyen")]
    bids_db.history_total = 3
    response = client.get("/auctions/1/bids?page=2&size=1")
    assert response.status_code == 200
    body = response.json()
    assert body["items"] == [{"id": 7, "bidder": "bi***", "amount": 25_000,
                              "created_at": "2026-10-20T12:00:00Z"}]
    assert (body["page"], body["size"], body["total"]) == (2, 1, 3)
    assert bids_db.history_args == (1, 2, 1)


def test_history_empty(client):
    response = client.get("/auctions/1/bids")
    assert response.status_code == 200
    assert response.json() == {"items": [], "page": 1, "size": 20, "total": 0}


def test_history_not_found(client):
    response = client.get("/auctions/999/bids")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "AUCTION_NOT_FOUND"


@pytest.mark.parametrize("url", [
    "/auctions/abc/bids", "/auctions/0/bids", "/auctions/1/bids?page=0",
    "/auctions/1/bids?size=0", "/auctions/1/bids?size=101",
])

def test_history_invalid_path_or_pagination(client, url):
    response = client.get(url)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


# API #11
def test_my_bids_response_and_token_user(client, bids_db):
    auction = bids_db.auctions[1]
    auction.highest_bidder_id = 2
    bids_db.mine_rows, bids_db.mine_total = [(auction, 20_000)], 1
    response = client.get("/users/me/bids?status=LEADING&page=2&size=5", headers=auth_header())
    assert response.status_code == 200
    body = response.json()
    assert (body["page"], body["size"], body["total"]) == (2, 5, 1)
    item = body["items"][0]
    assert item["my_status"] == "LEADING"
    assert item["my_highest_amount"] == 20_000
    assert item["auction"]["phase"] == "LIVE"
    assert set(item["auction"]) == {"id", "title", "status", "phase", "current_price", "end_time"}
    assert bids_db.mine_args == (2, "LEADING", 2, 5)


def test_my_bids_empty(client):
    response = client.get("/users/me/bids", headers=auth_header())
    assert response.status_code == 200
    assert response.json() == {"items": [], "page": 1, "size": 20, "total": 0}


@pytest.mark.parametrize("query", ["status=INVALID", "page=0", "size=0", "size=101"])

def test_my_bids_invalid_query(client, query):
    response = client.get(f"/users/me/bids?{query}", headers=auth_header())
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"