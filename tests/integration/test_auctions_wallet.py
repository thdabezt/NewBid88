"""End-to-end HTTP checks for the auction and wallet endpoints.

They run against the in-memory fakes, so they prove the router, the service
and the repository ports are wired together correctly.
"""

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.domain.entities import Auction, User, Wallet
from app.main import app, tokens
from tests.fakes import FakeUnitOfWork, InMemoryDb

NOW = datetime.now(UTC)


@pytest.fixture()
def db():
    store = InMemoryDb()
    store.users[1] = User(id=1, username="seller", password_hash="h", created_at=NOW)
    store.users[2] = User(id=2, username="buyer", password_hash="h", created_at=NOW)
    store.wallets[1] = Wallet(user_id=1, updated_at=NOW, balance=0, held=0)
    store.wallets[2] = Wallet(user_id=2, updated_at=NOW, balance=100_000, held=0)
    store.auctions[1] = Auction(
        id=1,
        seller_id=1,
        title="Vintage lamp",
        description="",
        category="home",
        starting_price=20_000,
        min_increment=1_000,
        current_price=20_000,
        bid_count=0,
        start_time=NOW - timedelta(minutes=5),
        end_time=NOW + timedelta(minutes=30),
        extended_count=0,
        status="OPEN",
        created_at=NOW,
    )
    return store


@pytest.fixture()
def client(db, monkeypatch):
    monkeypatch.setattr(app.state, "uow_factory", lambda: FakeUnitOfWork(db))
    with TestClient(app) as test_client:
        yield test_client


def auth_header(user_id=2):
    token, _ = tokens.issue(user_id, f"user_{user_id}")
    return {"Authorization": f"Bearer {token}"}


def test_browse_auctions_is_public_and_shows_the_seller(client):
    response = client.get("/auctions")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["title"] == "Vintage lamp"
    assert body["items"][0]["seller"] == {"id": 1, "username": "seller"}
    assert body["items"][0]["phase"] == "LIVE"


def test_read_auction_is_public(client):
    response = client.get("/auctions/1")
    assert response.status_code == 200
    assert response.json()["starting_price"] == 20_000
    assert response.json()["has_reserve"] is False


def test_read_missing_auction_is_404(client):
    response = client.get("/auctions/999")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "AUCTION_NOT_FOUND"


def test_create_auction_needs_a_token(client):
    response = client.post("/auctions", json={
        "title": "New thing", "category": "home", "starting_price": 20_000,
        "min_increment": 1_000, "end_time": (NOW + timedelta(hours=2)).isoformat(),
    })
    assert response.status_code == 401


def test_create_auction_stores_it(client, db):
    response = client.post("/auctions", headers=auth_header(1), json={
        "title": "New thing", "category": "home", "starting_price": 20_000,
        "min_increment": 1_000, "end_time": (NOW + timedelta(hours=2)).isoformat(),
    })
    assert response.status_code == 201
    assert response.json()["title"] == "New thing"
    assert len(db.auctions) == 2


def test_delete_auction_soft_deletes_it(client, db):
    response = client.delete("/auctions/1", headers=auth_header(1))
    assert response.status_code == 204
    assert db.auctions[1].deleted_at is not None


def test_delete_auction_of_another_seller_is_403(client, db):
    response = client.delete("/auctions/1", headers=auth_header(2))
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "NOT_OWNER"
    assert db.auctions[1].deleted_at is None


def test_my_auctions_lists_my_auctions(client):
    response = client.get("/users/me/auctions", headers=auth_header(1))
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["id"] == 1


def test_wallet_is_readable(client):
    response = client.get("/wallet", headers=auth_header(2))
    assert response.status_code == 200
    assert response.json() == {"balance": 100_000, "held": 0, "available": 100_000}


def test_top_up_adds_money_and_returns_the_new_wallet(client, db):
    response = client.post("/wallet/topups", headers=auth_header(2), json={"amount": 50_000})
    assert response.status_code == 201
    body = response.json()
    assert body["amount"] == 50_000
    assert body["wallet"] == {"balance": 150_000, "held": 0, "available": 150_000}
    assert db.wallets[2].balance == 150_000


def test_top_up_below_the_minimum_is_400(client, db):
    response = client.post("/wallet/topups", headers=auth_header(2), json={"amount": 100})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_AMOUNT"
    assert db.wallets[2].balance == 100_000


def test_transactions_are_listed_newest_first(client):
    client.post("/wallet/topups", headers=auth_header(2), json={"amount": 20_000})
    client.post("/wallet/topups", headers=auth_header(2), json={"amount": 30_000})
    response = client.get("/wallet/transactions", headers=auth_header(2))
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert [item["balance_delta"] for item in body["items"]] == [30_000, 20_000]
    assert body["items"][0]["type"] == "TOPUP"
