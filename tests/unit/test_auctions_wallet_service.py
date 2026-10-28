from datetime import UTC, datetime, timedelta

import pytest

from app.domain.entities import Auction, User, Wallet
from app.domain.errors import DomainError
from app.services.auctions import create_auction, delete_auction, get_auction, get_my_auctions, list_auctions
from app.services.wallet import get_wallet, list_transactions, top_up, wallet_response
from tests.fakes import FakeUnitOfWork, InMemoryDb

# The services read the real clock, so the fixtures are built around it.
NOW = datetime.now(UTC)


@pytest.fixture()
def db():
    store = InMemoryDb()
    store.users[1] = User(id=1, username="seller", password_hash="h", created_at=NOW)
    store.users[2] = User(id=2, username="buyer", password_hash="h", created_at=NOW)
    store.wallets[1] = Wallet(user_id=1, updated_at=NOW, balance=0, held=0)
    store.wallets[2] = Wallet(user_id=2, updated_at=NOW, balance=100_000, held=0)
    return store


def make_auction(db, **overrides):
    fields = dict(
        id=1,
        seller_id=1,
        title="Vintage lamp",
        description="",
        category="home",
        starting_price=20_000,
        min_increment=1_000,
        reserve_price=None,
        current_price=20_000,
        bid_count=0,
        highest_bid_id=None,
        highest_bidder_id=None,
        start_time=NOW - timedelta(minutes=5),
        end_time=NOW + timedelta(minutes=30),
        extended_count=0,
        status="OPEN",
        winner_id=None,
        final_price=None,
        closed_at=None,
        created_at=NOW,
        deleted_at=None,
    )
    fields.update(overrides)
    auction = Auction(**fields)
    db.auctions[auction.id] = auction
    return auction


# create_auction
def test_create_auction_stores_it_and_returns_detail(db):
    result = create_auction(
        FakeUnitOfWork(db), 1,
        title="Vintage lamp", description="Nice", category="home",
        starting_price=20_000, min_increment=1_000, reserve_price=None,
        start_time=None, end_time=NOW + timedelta(hours=2),
    )

    assert result["id"] == 1
    assert result["title"] == "Vintage lamp"
    assert result["seller"] == {"id": 1, "username": "seller"}
    assert result["current_price"] == 20_000
    assert result["phase"] == "LIVE"
    assert result["status"] == "OPEN"
    assert db.auctions[1].title == "Vintage lamp"
    assert db.auctions[1].status == "OPEN"


def test_create_auction_rejects_price_below_1000(db):
    with pytest.raises(DomainError) as error:
        create_auction(
            FakeUnitOfWork(db), 1,
            title="x", description=None, category="home",
            starting_price=999, min_increment=1_000, reserve_price=None,
            start_time=None, end_time=NOW + timedelta(hours=2),
        )
    assert error.value.code == "INVALID_PRICE"
    assert db.auctions == {}


def test_create_auction_rejects_reserve_below_starting_price(db):
    with pytest.raises(DomainError) as error:
        create_auction(
            FakeUnitOfWork(db), 1,
            title="x", description=None, category="home",
            starting_price=20_000, min_increment=1_000, reserve_price=19_000,
            start_time=None, end_time=NOW + timedelta(hours=2),
        )
    assert error.value.code == "INVALID_PRICE"


def test_create_auction_rejects_duration_too_short(db):
    with pytest.raises(DomainError) as error:
        create_auction(
            FakeUnitOfWork(db), 1,
            title="x", description=None, category="home",
            starting_price=20_000, min_increment=1_000, reserve_price=None,
            start_time=None, end_time=NOW + timedelta(seconds=10),
        )
    assert error.value.code == "INVALID_TIME_RANGE"


# list_auctions
def test_list_auctions_returns_live_auctions_with_seller(db):
    make_auction(db)
    make_auction(db, id=2, title="Ended", end_time=NOW - timedelta(minutes=1))
    make_auction(db, id=3, title="Later", start_time=NOW + timedelta(minutes=10))

    items, total = list_auctions(FakeUnitOfWork(db), state="LIVE")

    assert total == 1
    assert [item["id"] for item in items] == [1]
    assert items[0]["seller"]["username"] == "seller"


def test_list_auctions_filters_by_state(db):
    make_auction(db)
    make_auction(db, id=2, title="Ended", end_time=NOW - timedelta(minutes=1))
    make_auction(db, id=3, title="Later", start_time=NOW + timedelta(minutes=10))

    upcoming, _ = list_auctions(FakeUnitOfWork(db), state="UPCOMING")
    finished, _ = list_auctions(FakeUnitOfWork(db), state="FINISHED")

    assert [item["id"] for item in upcoming] == [3]
    assert [item["id"] for item in finished] == [2]


def test_list_auctions_filters_by_price_and_seller(db):
    make_auction(db, current_price=20_000)
    make_auction(db, id=2, current_price=50_000, seller_id=2)

    items, total = list_auctions(FakeUnitOfWork(db), state="LIVE", min_price=30_000)
    assert total == 1
    assert items[0]["id"] == 2

    items, total = list_auctions(FakeUnitOfWork(db), state="LIVE", seller_id=1)
    assert [item["id"] for item in items] == [1]


def test_list_auctions_hides_deleted(db):
    make_auction(db, deleted_at=NOW)
    items, total = list_auctions(FakeUnitOfWork(db), state="LIVE")
    assert items == []
    assert total == 0


def test_list_auctions_rejects_bad_pagination(db):
    with pytest.raises(DomainError) as error:
        list_auctions(FakeUnitOfWork(db), state="LIVE", page=0)
    assert error.value.code == "INVALID_PAGE"

    with pytest.raises(DomainError) as error:
        list_auctions(FakeUnitOfWork(db), state="LIVE", size=101)
    assert error.value.code == "INVALID_PAGE_SIZE"


def test_list_auctions_rejects_price_range_inverted(db):
    with pytest.raises(DomainError) as error:
        list_auctions(FakeUnitOfWork(db), state="LIVE", min_price=90_000, max_price=10_000)
    assert error.value.code == "INVALID_PRICE_RANGE"


# get_auction
def test_get_auction_masks_the_leader(db):
    make_auction(db, highest_bidder_id=2, bid_count=1)
    result = get_auction(FakeUnitOfWork(db), 1)
    assert result["highest_bidder"] == "bu***"
    assert result["has_reserve"] is False
    assert result["reserve_met"] is None


def test_get_auction_reports_missing_and_deleted(db):
    with pytest.raises(DomainError) as error:
        get_auction(FakeUnitOfWork(db), 99)
    assert error.value.code == "AUCTION_NOT_FOUND"

    make_auction(db, deleted_at=NOW)
    with pytest.raises(DomainError) as error:
        get_auction(FakeUnitOfWork(db), 1)
    assert error.value.code == "AUCTION_NOT_FOUND"


# delete_auction
def test_delete_auction_marks_it_deleted(db):
    make_auction(db)
    delete_auction(FakeUnitOfWork(db), 1, 1)
    assert db.auctions[1].deleted_at is not None


def test_delete_auction_rejects_other_seller(db):
    make_auction(db)
    with pytest.raises(DomainError) as error:
        delete_auction(FakeUnitOfWork(db), 1, 2)
    assert error.value.code == "NOT_OWNER"
    assert db.auctions[1].deleted_at is None


def test_delete_auction_rejects_auction_with_bids(db):
    make_auction(db, bid_count=1)
    with pytest.raises(DomainError) as error:
        delete_auction(FakeUnitOfWork(db), 1, 1)
    assert error.value.code == "AUCTION_HAS_BIDS"
    assert db.auctions[1].deleted_at is None


def test_delete_auction_rejects_finished_auction(db):
    make_auction(db, end_time=NOW - timedelta(minutes=1))
    with pytest.raises(DomainError) as error:
        delete_auction(FakeUnitOfWork(db), 1, 1)
    assert error.value.code == "AUCTION_NOT_CANCELLABLE"
    assert db.auctions[1].deleted_at is None


# get_my_auctions
def test_my_auctions_lists_only_my_auctions(db):
    make_auction(db)
    make_auction(db, id=2, seller_id=2)

    items, total = get_my_auctions(FakeUnitOfWork(db), 1)

    assert total == 1
    assert items[0]["id"] == 1
    assert items[0]["seller"]["username"] == "seller"
    assert items[0]["reserve_price"] is None


def test_my_auctions_filters_by_status(db):
    make_auction(db)
    make_auction(db, id=2, status="SOLD", winner_id=2, final_price=20_000)

    items, total = get_my_auctions(FakeUnitOfWork(db), 1, status="SOLD")

    assert total == 1
    assert items[0]["id"] == 2
    assert items[0]["winner"] == "bu***"


# wallet
def test_get_wallet_returns_balances(db):
    wallet = get_wallet(FakeUnitOfWork(db), 2)
    assert wallet_response(wallet) == {"balance": 100_000, "held": 0, "available": 100_000}


def test_get_wallet_rejects_unknown_user(db):
    with pytest.raises(DomainError) as error:
        get_wallet(FakeUnitOfWork(db), 99)
    assert error.value.code == "WALLET_NOT_FOUND"


def test_top_up_adds_money_and_writes_ledger(db):
    transaction, wallet = top_up(FakeUnitOfWork(db), 2, 50_000)

    assert wallet.balance == 150_000
    assert transaction.type == "TOPUP"
    assert transaction.balance_delta == 50_000
    assert transaction.balance_after == 150_000
    assert db.wallets[2].balance == 150_000
    assert db.transactions[0].type == "TOPUP"


def test_top_up_rejects_amount_outside_limits(db):
    with pytest.raises(DomainError) as error:
        top_up(FakeUnitOfWork(db), 2, 9_999)
    assert error.value.code == "INVALID_AMOUNT"

    with pytest.raises(DomainError) as error:
        top_up(FakeUnitOfWork(db), 2, 50_000_001)
    assert error.value.code == "INVALID_AMOUNT"

    assert db.wallets[2].balance == 100_000
    assert db.transactions == []


def test_list_transactions_filters_by_type(db):
    top_up(FakeUnitOfWork(db), 2, 20_000)
    top_up(FakeUnitOfWork(db), 2, 30_000)

    items, total = list_transactions(FakeUnitOfWork(db), 2, "TOPUP", 1, 20)
    assert total == 2
    assert [item.balance_delta for item in items] == [30_000, 20_000]

    items, total = list_transactions(FakeUnitOfWork(db), 2, "BID_HOLD", 1, 20)
    assert items == []
    assert total == 0
