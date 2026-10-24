from datetime import timedelta
from types import SimpleNamespace

import pytest

from app.domain.errors import DomainError
from app.services.bids import bid_history, my_bids, place_bid
from tests.fakes import FakeBidsUnitOfWork


# API #8
def test_first_bid_holds_money_and_updates_auction(bids_db):
    uow = FakeBidsUnitOfWork(bids_db)
    result = place_bid(uow, 2, 1, 20_000)

    assert result["wallet"] == {"balance": 100_000, "held": 20_000, "available": 80_000}
    assert result["auction"]["bid_count"] == 1
    assert bids_db.auctions[1].highest_bidder_id == 2
    assert bids_db.auctions[1].highest_bid_id == result["bid"]["id"]
    assert bids_db.auctions[1].current_price == 20_000
    assert bids_db.bids[0].bidder_id == 2
    assert bids_db.ledger[0]["type"] == "BID_HOLD"
    assert bids_db.ledger[0]["held_delta"] == 20_000
    assert bids_db.ledger[0]["balance_delta"] == 0
    assert uow.commits == 1


def test_outbid_releases_only_this_auctions_hold(bids_db):
    bids_db.wallets[2].held = 10_000
    first = place_bid(FakeBidsUnitOfWork(bids_db), 2, 1, 20_000)
    place_bid(FakeBidsUnitOfWork(bids_db), 3, 1, 25_000)

    assert bids_db.wallets[2].held == 10_000
    assert bids_db.wallets[3].held == 25_000
    assert bids_db.wallets[2].balance == bids_db.wallets[3].balance == 100_000
    release = bids_db.ledger[-1]
    assert release["type"] == "BID_RELEASE"
    assert release["held_delta"] == -20_000
    assert release["bid_id"] == first["bid"]["id"]
    assert release["held_after"] == 10_000


@pytest.mark.parametrize("case, code", [
    ("missing", "AUCTION_NOT_FOUND"), ("deleted", "AUCTION_NOT_FOUND"),
    ("closed", "AUCTION_NOT_ACTIVE"), ("expired", "AUCTION_NOT_ACTIVE"),
    ("upcoming", "AUCTION_NOT_STARTED"), ("seller", "SELLER_CANNOT_BID"),
    ("leader", "ALREADY_HIGHEST_BIDDER"),
])

def test_bid_rejects_invalid_auction_or_bidder(bids_db, bids_now, case, code):
    auction = bids_db.auctions[1]
    user_id = 2
    if case == "missing":
        bids_db.auctions.clear()
    elif case == "deleted":
        auction.deleted_at = bids_now
    elif case == "closed":
        auction.status = "SOLD"
    elif case == "expired":
        auction.end_time = bids_now
    elif case == "upcoming":
        auction.start_time = bids_now + timedelta(minutes=1)
    elif case == "seller":
        user_id = 1
    elif case == "leader":
        auction.highest_bidder_id = 2
    uow = FakeBidsUnitOfWork(bids_db)

    with pytest.raises(DomainError) as error:
        place_bid(uow, user_id, 1, 20_000)

    assert error.value.code == code
    assert uow.commits == 0
    assert bids_db.bids == bids_db.ledger == []
    assert bids_db.wallets[2].held == 0


@pytest.mark.parametrize("has_previous_bid, minimum", [(False, 20_000), (True, 25_000)])

def test_bid_rejects_price_below_minimum(bids_db, has_previous_bid, minimum):
    if has_previous_bid:
        place_bid(FakeBidsUnitOfWork(bids_db), 3, 1, 20_000)
    with pytest.raises(DomainError) as error:
        place_bid(FakeBidsUnitOfWork(bids_db), 2, 1, minimum - 1)
    assert error.value.code == "BID_TOO_LOW"
    assert error.value.details == {"min_required": minimum}


def test_bid_checks_available_money_not_balance(bids_db):
    bids_db.wallets[2].held = 90_000
    with pytest.raises(DomainError) as error:
        place_bid(FakeBidsUnitOfWork(bids_db), 2, 1, 20_000)
    assert error.value.code == "INSUFFICIENT_FUNDS"
    assert error.value.details == {"available": 10_000}
    assert bids_db.wallets[2].held == 90_000
    assert bids_db.bids == bids_db.ledger == []


@pytest.mark.parametrize("seconds_left, extended", [(61, False), (60, True), (30, True)])

def test_anti_sniping(bids_db, bids_now, seconds_left, extended):
    bids_db.auctions[1].end_time = bids_now + timedelta(seconds=seconds_left)
    result = place_bid(FakeBidsUnitOfWork(bids_db), 2, 1, 20_000)
    assert result["auction"]["extended"] is extended
    assert bids_db.auctions[1].extended_count == int(extended)
    assert bids_db.auctions[1].end_time == bids_now + timedelta(seconds=max(seconds_left, 60))


# API #9
def test_history_masks_username_and_passes_pagination(bids_db, bids_now):
    bid = SimpleNamespace(id=7, amount=25_000, created_at=bids_now)
    bids_db.history_rows = [(bid, "binh_nguyen")]
    bids_db.history_total = 3
    uow = FakeBidsUnitOfWork(bids_db)
    result = bid_history(uow, 1, 2, 1)
    assert result == {"items": [{"id": 7, "bidder": "bi***", "amount": 25_000,
                                 "created_at": bids_now}], "page": 2, "size": 1, "total": 3}
    assert bids_db.history_args == (1, 2, 1)
    assert uow.is_read_only and uow.commits == 0


def test_history_without_bids(bids_db):
    assert bid_history(FakeBidsUnitOfWork(bids_db), 1, 1, 20) == {
        "items": [], "page": 1, "size": 20, "total": 0,
    }


@pytest.mark.parametrize("deleted", [False, True])

def test_history_rejects_missing_or_deleted_auction(bids_db, bids_now, deleted):
    if deleted:
        bids_db.auctions[1].deleted_at = bids_now
    else:
        bids_db.auctions.clear()
    with pytest.raises(DomainError) as error:
        bid_history(FakeBidsUnitOfWork(bids_db), 1, 1, 20)
    assert error.value.code == "AUCTION_NOT_FOUND"


# API #11
@pytest.mark.parametrize("status, leader, winner, expected", [
    ("OPEN", 2, None, "LEADING"), ("OPEN", 3, None, "OUTBID"),
    ("SOLD", 2, 2, "WON"), ("SOLD", 3, 3, "LOST"),
    ("UNSOLD", 2, None, "NO_SALE"),
])

def test_my_bids_status(bids_db, status, leader, winner, expected):
    auction = bids_db.auctions[1]
    auction.status, auction.highest_bidder_id, auction.winner_id = status, leader, winner
    bids_db.mine_rows, bids_db.mine_total = [(auction, 20_000)], 1
    uow = FakeBidsUnitOfWork(bids_db)
    result = my_bids(uow, 2, expected, 2, 5)
    assert result["items"][0]["my_status"] == expected
    assert result["items"][0]["my_highest_amount"] == 20_000
    assert "reserve_price" not in result["items"][0]["auction"]
    assert (result["page"], result["size"], result["total"]) == (2, 5, 1)
    assert bids_db.mine_args == (2, expected, 2, 5)
    assert uow.is_read_only and uow.commits == 0


@pytest.mark.parametrize("phase", ["UPCOMING", "LIVE", "FINISHED"])

def test_my_bids_phase_for_open_auction(bids_db, bids_now, phase):
    auction = bids_db.auctions[1]
    auction.highest_bidder_id = 2
    if phase == "UPCOMING":
        auction.start_time = bids_now + timedelta(minutes=1)
    elif phase == "FINISHED":
        auction.end_time = bids_now
    bids_db.mine_rows, bids_db.mine_total = [(auction, 20_000)], 1
    item = my_bids(FakeBidsUnitOfWork(bids_db), 2, None, 1, 20)["items"][0]
    assert item["auction"]["phase"] == phase
    assert item["my_status"] == "LEADING"


def test_my_bids_empty(bids_db):
    assert my_bids(FakeBidsUnitOfWork(bids_db), 2, None, 1, 20) == {
        "items": [], "page": 1, "size": 20, "total": 0,
    }