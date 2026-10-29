from datetime import timedelta

import pytest

from app.domain.entities import Auction, User, Wallet
from app.domain.errors import NotFoundError
from app.services.settlement import SettlementService
from tests.fakes import FakeUnitOfWork, FixedClock, InMemoryDb

clock = FixedClock()
NOW = clock.now()


@pytest.fixture()
def db():
    store = InMemoryDb()
    for user_id, name in ((1, "seller"), (2, "buyer")):
        store.users[user_id] = User(id=user_id, username=name, password_hash="h", created_at=NOW)
    store.wallets[1] = Wallet(user_id=1, updated_at=NOW, balance=0, held=0)
    store.wallets[2] = Wallet(user_id=2, updated_at=NOW, balance=100_000, held=30_000)
    return store


@pytest.fixture()
def service(db):
    return SettlementService(lambda: FakeUnitOfWork(db), clock)


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
        current_price=30_000,
        bid_count=2,
        highest_bid_id=7,
        highest_bidder_id=2,
        start_time=NOW - timedelta(hours=1),
        end_time=NOW - timedelta(seconds=1),
        extended_count=0,
        status="OPEN",
        created_at=NOW - timedelta(hours=1),
    )
    fields.update(overrides)
    auction = Auction(**fields)
    db.auctions[auction.id] = auction
    return auction


def ledger(db):
    return [(t.user_id, t.type, t.balance_delta, t.held_delta, t.auction_id, t.bid_id) for t in db.transactions]


def test_sold_moves_money_from_winner_to_seller(db, service):
    make_auction(db)

    assert service.settle(1) == "SOLD"

    auction = db.auctions[1]
    assert (auction.status, auction.winner_id, auction.final_price, auction.closed_at) == ("SOLD", 2, 30_000, NOW)
    assert (db.wallets[2].balance, db.wallets[2].held) == (70_000, 0)
    assert (db.wallets[1].balance, db.wallets[1].held) == (30_000, 0)
    assert ledger(db) == [
        (1, "SETTLEMENT_RECEIVE", 30_000, 0, 1, 7),
        (2, "SETTLEMENT_PAY", -30_000, -30_000, 1, 7),
    ]


def test_wallets_are_locked_in_ascending_user_id(db, service):
    db.users[3] = User(id=3, username="late_seller", password_hash="h", created_at=NOW)
    db.wallets[3] = Wallet(user_id=3, updated_at=NOW)
    make_auction(db, seller_id=3)

    service.settle(1)

    assert [t.user_id for t in db.transactions] == [2, 3]


def test_no_bids_is_unsold_without_ledger_rows(db, service):
    make_auction(db, current_price=20_000, bid_count=0, highest_bid_id=None, highest_bidder_id=None)

    assert service.settle(1) == "UNSOLD"

    auction = db.auctions[1]
    assert (auction.status, auction.winner_id, auction.final_price, auction.closed_at) == ("UNSOLD", None, None, NOW)
    assert db.transactions == []


def test_reserve_not_met_is_unsold_and_releases_hold(db, service):
    make_auction(db, reserve_price=50_000)

    assert service.settle(1) == "UNSOLD"

    assert db.auctions[1].final_price is None
    assert (db.wallets[2].balance, db.wallets[2].held) == (100_000, 0)
    assert db.wallets[1].balance == 0
    assert ledger(db) == [(2, "BID_RELEASE", 0, -30_000, 1, 7)]


def test_reserve_exactly_met_is_sold(db, service):
    make_auction(db, reserve_price=30_000)

    assert service.settle(1) == "SOLD"


def test_settles_at_exact_end_time(db, service):
    make_auction(db, end_time=NOW)

    assert service.settle(1) == "SOLD"


@pytest.mark.parametrize(
    "overrides",
    [
        {"end_time": NOW + timedelta(seconds=1)},
        {"deleted_at": NOW - timedelta(minutes=1), "bid_count": 0, "highest_bidder_id": None},
        {"status": "SOLD"},
        {"status": "UNSOLD"},
    ],
    ids=["not_ended", "deleted", "already_sold", "already_unsold"],
)
def test_skips_auctions_that_cannot_be_settled(db, service, overrides):
    before = make_auction(db, **overrides)

    assert service.settle(1) is None

    assert db.auctions[1] == before
    assert db.transactions == []


def test_missing_auction_is_skipped(service):
    assert service.settle(99) is None


def test_settling_twice_moves_money_once(db, service):
    make_auction(db)

    service.settle(1)
    assert service.settle(1) is None

    assert (db.wallets[2].balance, db.wallets[1].balance) == (70_000, 30_000)
    assert len(db.transactions) == 2


def test_missing_wallet_rolls_back_everything(db, service):
    make_auction(db)
    del db.wallets[1]

    with pytest.raises(NotFoundError):
        service.settle(1)

    assert db.auctions[1].status == "OPEN"
    assert db.transactions == []
    assert db.wallets[2].held == 30_000


def test_due_lists_ended_open_auctions_by_end_time(db, service):
    make_auction(db, id=1, end_time=NOW - timedelta(seconds=5))
    make_auction(db, id=2, end_time=NOW - timedelta(seconds=30))
    make_auction(db, id=3, end_time=NOW)
    make_auction(db, id=4, end_time=NOW + timedelta(seconds=1))
    make_auction(db, id=5, status="SOLD")
    make_auction(db, id=6, deleted_at=NOW)

    assert service.due(10) == [2, 1, 3]
    assert service.due(2) == [2, 1]
