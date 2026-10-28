from datetime import datetime, timedelta, timezone
from dataclasses import replace
from types import SimpleNamespace

import pytest

from app.domain.errors import ConflictError, DomainError, ForbiddenError, NotFoundError, ValidationError
from app.services import auctions as service


UTC = timezone.utc
NOW = datetime(2026, 10, 20, 12, 0, tzinfo=UTC)


def make_auction(**overrides):
    values = {
        "id": 1,
        "seller_id": 1,
        "title": "Test auction",
        "description": "Description",
        "category": "watches",
        "starting_price": 10_000,
        "min_increment": 1_000,
        "reserve_price": None,
        "current_price": 10_000,
        "bid_count": 0,
        "status": "OPEN",
        "start_time": NOW - timedelta(minutes=1),
        "end_time": NOW + timedelta(minutes=10),
        "extended_count": 0,
        "highest_bidder_id": None,
        "final_price": None,
        "closed_at": None,
        "created_at": NOW,
        "winner_id": None,
        "deleted_at": None,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


class FakeUsers:
    def __init__(self, users=None):
        self.rows = (
            users
            if users is not None
            else {
                1: SimpleNamespace(id=1, username="seller"),
                2: SimpleNamespace(id=2, username="bidder"),
                3: SimpleNamespace(id=3, username="winner"),
            }
        )
        self.get_calls = []

    def get(self, user_id):
        self.get_calls.append(user_id)
        return self.rows.get(user_id)

    def get_many(self, ids):
        return {user_id: self.rows[user_id] for user_id in ids if user_id in self.rows}


class FakeAuctions:
    def __init__(self, rows=None, list_result=None, seller_result=None):
        self.rows = {row.id: row for row in rows or []}
        self.list_result = list_result or ([], 0)
        self.seller_result = seller_result or ([], 0)
        self.added = []
        self.list_args = None
        self.seller_args = None
        self.get_calls = []
        self.lock_calls = []
        self.deleted = []

    def add(self, auction):
        self.added.append(auction)
        auction = replace(auction, id=max(self.rows, default=0) + 1)
        self.rows[auction.id] = auction
        return auction

    def get(self, auction_id):
        self.get_calls.append(auction_id)
        return self.rows.get(auction_id)

    def lock_for_update(self, auction_id):
        self.lock_calls.append(auction_id)
        return self.rows.get(auction_id)

    def list_visible(self, **kwargs):
        self.list_args = kwargs
        return self.list_result

    def list_for_seller(self, seller_id, status, page, size):
        self.seller_args = (seller_id, status, page, size)
        return self.seller_result

    def mark_deleted(self, auction_id, deleted_at):
        auction = self.rows[auction_id]
        auction.deleted_at = deleted_at
        self.deleted.append((auction_id, deleted_at))


class FakeUow:
    def __init__(self, *, users=None, rows=None, list_result=None, seller_result=None):
        self.users = FakeUsers(users)
        self.auctions = FakeAuctions(rows, list_result, seller_result)
        self.commits = 0
        self.read_only_calls = 0
        self.entered = 0

    def __enter__(self):
        self.entered += 1
        return self

    def __exit__(self, exc_type, exc, tb):
        return None

    def commit(self):
        self.commits += 1

    def read_only(self):
        self.read_only_calls += 1


@pytest.fixture(autouse=True)
def fixed_service_time(monkeypatch):
    class FrozenDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return NOW

    monkeypatch.setattr(service, "datetime", FrozenDateTime)


def create_kwargs(**overrides):
    values = {
        "title": "Test auction",
        "description": "Description",
        "category": "watches",
        "starting_price": 10_000,
        "min_increment": 1_000,
        "reserve_price": None,
        "start_time": NOW,
        "end_time": NOW + timedelta(minutes=1),
    }
    values.update(overrides)
    return values


def test_create_auction_sets_initial_state_and_commits():
    uow = FakeUow()

    result = service.create_auction(uow, 1, **create_kwargs())

    assert result["id"] == 1
    assert result["status"] == "OPEN"
    assert result["phase"] == "LIVE"
    assert result["current_price"] == 10_000
    assert result["bid_count"] == 0
    assert result["starting_price"] == 10_000
    assert result["description"] == "Description"
    assert result["has_reserve"] is False
    assert result["reserve_met"] is None
    assert uow.auctions.added[0].extended_count == 0
    assert uow.commits == 1
    assert uow.users.get_calls == [1]


def test_create_auction_defaults_start_time_to_now_and_normalizes_timezone():
    uow = FakeUow()
    start = NOW.astimezone(timezone(timedelta(hours=7)))
    end = start + timedelta(minutes=1)

    result = service.create_auction(
        uow,
        1,
        **create_kwargs(start_time=None, end_time=end),
    )

    assert uow.auctions.added[0].start_time == NOW
    assert uow.auctions.added[0].end_time == NOW + timedelta(minutes=1)
    assert result["start_time"] == NOW


@pytest.mark.parametrize(
    "overrides",
    [
        {"starting_price": 999},
        {"starting_price": -1},
        {"min_increment": 999},
        {"min_increment": 0},
        {"reserve_price": 9_999},
        {"reserve_price": -1},
    ],
)
def test_create_auction_rejects_invalid_prices(overrides):
    uow = FakeUow()

    with pytest.raises(DomainError) as exc_info:
        service.create_auction(uow, 1, **create_kwargs(**overrides))

    assert exc_info.value.code == "INVALID_PRICE"
    assert uow.entered == 0
    assert uow.commits == 0


@pytest.mark.parametrize(
    "overrides",
    [
        {"start_time": NOW.replace(tzinfo=None)},
        {"end_time": (NOW + timedelta(minutes=1)).replace(tzinfo=None)},
        {"start_time": NOW - timedelta(seconds=5, microseconds=1)},
        {"start_time": NOW + timedelta(days=30, microseconds=1)},
        {"end_time": NOW + timedelta(seconds=59)},
        {"end_time": NOW + timedelta(days=30, microseconds=1)},
    ],
)
def test_create_auction_rejects_invalid_time_ranges(overrides):
    uow = FakeUow()

    with pytest.raises(DomainError) as exc_info:
        service.create_auction(uow, 1, **create_kwargs(**overrides))

    assert exc_info.value.code == "INVALID_TIME_RANGE"
    assert uow.entered == 0
    assert uow.commits == 0


def test_create_auction_accepts_time_boundaries():
    uow = FakeUow()
    start = NOW + timedelta(days=30)

    service.create_auction(
        uow,
        1,
        **create_kwargs(
            start_time=start,
            end_time=start + timedelta(days=30),
        ),
    )

    assert uow.commits == 1


def test_create_auction_rejects_missing_seller():
    uow = FakeUow(users={})

    with pytest.raises(NotFoundError) as exc_info:
        service.create_auction(uow, 99, **create_kwargs())

    assert exc_info.value.code == "USER_NOT_FOUND"
    assert uow.commits == 0


@pytest.mark.parametrize("state", ["LIVE", "UPCOMING", "FINISHED"])
@pytest.mark.parametrize("sort", ["ending_soon", "newest", "price_asc", "price_desc"])
def test_list_auctions_passes_filters_and_maps_seller(state, sort):
    auction = make_auction()
    uow = FakeUow(list_result=([auction], 7))

    items, total = service.list_auctions(
        uow,
        state=state,
        q="watch",
        category="watches",
        seller_id=1,
        min_price=2_000,
        max_price=20_000,
        sort=sort,
        page=2,
        size=5,
    )

    assert total == 7
    assert len(items) == 1
    assert items[0]["seller"] == {"id": 1, "username": "seller"}
    assert items[0]["phase"] == "LIVE"
    state_filters = {
        "LIVE": {"status": "OPEN", "starts_before": NOW, "ends_after": NOW},
        "UPCOMING": {"status": "OPEN", "starts_after": NOW},
        "FINISHED": {"ends_before": NOW},
    }
    assert uow.auctions.list_args == {
        "title_contains": "watch",
        "category": "watches",
        "seller_id": 1,
        "min_price": 2_000,
        "max_price": 20_000,
        "sort": sort,
        "page": 2,
        "size": 5,
        **state_filters[state],
    }
    assert uow.read_only_calls == 1
    assert uow.commits == 0


@pytest.mark.parametrize(
    "kwargs,code",
    [
        ({"page": 0}, "INVALID_PAGE"),
        ({"page": -1}, "INVALID_PAGE"),
        ({"size": 0}, "INVALID_PAGE_SIZE"),
        ({"size": 101}, "INVALID_PAGE_SIZE"),
        ({"min_price": 2_000, "max_price": 1_000}, "INVALID_PRICE_RANGE"),
        ({"sort": "unknown"}, "INVALID_SORT"),
    ],
)
def test_list_auctions_rejects_invalid_filters(kwargs, code):
    uow = FakeUow()

    with pytest.raises(ValidationError) as exc_info:
        service.list_auctions(uow, **kwargs)

    assert exc_info.value.code == code
    assert uow.entered == 0


@pytest.mark.parametrize(
    "auction,expected_phase",
    [
        (make_auction(start_time=NOW + timedelta(seconds=1)), "UPCOMING"),
        (make_auction(), "LIVE"),
        (make_auction(end_time=NOW), "FINISHED"),
        (make_auction(status="SOLD"), "FINISHED"),
        (make_auction(status="UNSOLD"), "FINISHED"),
    ],
)
def test_get_auction_returns_detail_and_phase(auction, expected_phase):
    auction.highest_bidder_id = 2
    auction.reserve_price = 15_000
    uow = FakeUow(rows=[auction])

    result = service.get_auction(uow, auction.id)

    assert result["phase"] == expected_phase
    assert result["seller"]["username"] == "seller"
    assert result["highest_bidder"] == "bi***"
    assert result["has_reserve"] is True
    assert result["reserve_met"] is False
    assert uow.users.get_calls == [1, 2]
    assert uow.read_only_calls == 1


def test_get_auction_without_leader_and_reserve():
    uow = FakeUow(rows=[make_auction()])

    result = service.get_auction(uow, 1)

    assert result["highest_bidder"] is None
    assert result["has_reserve"] is False
    assert result["reserve_met"] is None


@pytest.mark.parametrize(
    "auction,users",
    [
        (None, {1: SimpleNamespace(id=1, username="seller")}),
        (make_auction(seller_id=2), {1: SimpleNamespace(id=1, username="seller")}),
    ],
)
def test_get_auction_not_found_errors(auction, users):
    uow = FakeUow(users=users, rows=[auction] if auction else [])

    with pytest.raises(NotFoundError) as exc_info:
        service.get_auction(uow, 1)

    assert exc_info.value.code == "AUCTION_NOT_FOUND"


@pytest.mark.parametrize(
    "auction,user_id,error_type,code",
    [
        (None, 1, NotFoundError, "AUCTION_NOT_FOUND"),
        (make_auction(seller_id=2), 1, ForbiddenError, "NOT_OWNER"),
        (make_auction(bid_count=1), 1, ConflictError, "AUCTION_HAS_BIDS"),
        (make_auction(status="SOLD"), 1, ConflictError, "AUCTION_NOT_CANCELLABLE"),
        (
            make_auction(end_time=NOW),
            1,
            ConflictError,
            "AUCTION_NOT_CANCELLABLE",
        ),
    ],
)
def test_delete_auction_rejects_invalid_state(auction, user_id, error_type, code):
    uow = FakeUow(rows=[auction] if auction else [])

    with pytest.raises(error_type) as exc_info:
        service.delete_auction(uow, 1, user_id)

    assert exc_info.value.code == code
    assert uow.auctions.lock_calls == [1]
    assert uow.commits == 0
    assert not uow.auctions.deleted


def test_delete_auction_soft_deletes_under_lock_and_commits():
    auction = make_auction()
    uow = FakeUow(rows=[auction])

    result = service.delete_auction(uow, auction.id, 1)

    assert result is None
    assert uow.auctions.rows[auction.id].deleted_at == NOW
    assert uow.auctions.lock_calls == [1]
    assert uow.auctions.deleted == [(auction.id, NOW)]
    assert uow.commits == 1


@pytest.mark.parametrize(
    "kwargs,code",
    [
        ({"page": 0}, "INVALID_PAGE"),
        ({"size": 0}, "INVALID_PAGE_SIZE"),
        ({"size": 101}, "INVALID_PAGE_SIZE"),
    ],
)
def test_get_my_auctions_rejects_invalid_pagination(kwargs, code):
    uow = FakeUow()

    with pytest.raises(ValidationError) as exc_info:
        service.get_my_auctions(uow, 1, **kwargs)

    assert exc_info.value.code == code
    assert uow.entered == 0


def test_get_my_auctions_returns_seller_auctions_and_masks_winner():
    won = make_auction(id=2, status="SOLD", winner_id=3, final_price=12_000)
    no_winner = make_auction(id=1, reserve_price=20_000)
    uow = FakeUow(seller_result=([won, no_winner], 2))

    items, total = service.get_my_auctions(uow, 1, status="SOLD", page=2, size=5)

    assert total == 2
    assert [item["id"] for item in items] == [2, 1]
    assert items[0]["seller"]["username"] == "seller"
    assert items[0]["winner"] == "wi***"
    assert items[0]["reserve_price"] is None
    assert items[0]["final_price"] == 12_000
    assert items[1]["winner"] is None
    assert uow.auctions.seller_args == (1, "SOLD", 2, 5)
    assert uow.read_only_calls == 1
    assert uow.commits == 0


def test_get_my_auctions_rejects_missing_seller():
    uow = FakeUow(users={})

    with pytest.raises(NotFoundError) as exc_info:
        service.get_my_auctions(uow, 99)

    assert exc_info.value.code == "USER_NOT_FOUND"
    assert uow.auctions.seller_args is None
