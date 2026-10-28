"""In-memory stand-ins for the domain ports, for tests that should not need PostgreSQL."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from copy import deepcopy
from types import SimpleNamespace

from app.domain.entities import Auction, User, Wallet, WalletTransaction
from app.domain.errors import NotFoundError, UsernameTaken


class InMemoryDb:
    def __init__(self) -> None:
        self.users: dict[int, User] = {}
        self.wallets: dict[int, Wallet] = {}
        self.auctions: dict[int, Auction] = {}
        self.transactions: list[WalletTransaction] = []


class FakeUserRepository:
    def __init__(self, rows: dict[int, User]) -> None:
        self.rows = rows

    def add(self, user: User) -> User:
        if any(row.username == user.username for row in self.rows.values()):
            raise UsernameTaken(user.username)
        stored = replace(user, id=max(self.rows, default=0) + 1)
        self.rows[stored.id] = stored
        return stored

    def get(self, id: int) -> User | None:
        return self.rows.get(id)

    def get_by_username(self, username: str) -> User | None:
        return next((row for row in self.rows.values() if row.username == username), None)

    def get_many(self, ids: list[int]) -> dict[int, User]:
        return {id: self.rows[id] for id in ids if id in self.rows}


class FakeWalletRepository:
    def __init__(self, rows: dict[int, Wallet], transactions: list[WalletTransaction]) -> None:
        self.rows = rows
        self.transactions = transactions

    def add(self, wallet: Wallet) -> None:
        self.rows[wallet.user_id] = wallet

    def get(self, user_id: int) -> Wallet | None:
        return self.rows.get(user_id)

    def credit(self, user_id: int, amount: int, now: datetime) -> tuple[WalletTransaction, Wallet]:
        wallet = self.rows.get(user_id)
        if wallet is None:
            raise NotFoundError("WALLET_NOT_FOUND", "Wallet not found")
        wallet = replace(wallet, balance=wallet.balance + amount, updated_at=now)
        self.rows[user_id] = wallet
        transaction = WalletTransaction(
            id=len(self.transactions) + 1,
            user_id=user_id,
            type="TOPUP",
            balance_delta=amount,
            held_delta=0,
            balance_after=wallet.balance,
            held_after=wallet.held,
            created_at=now,
        )
        self.transactions.append(transaction)
        return transaction, wallet

    def list_transactions(
        self, user_id: int, transaction_type: str | None, page: int, size: int
    ) -> tuple[list[WalletTransaction], int]:
        rows = [t for t in self.transactions if t.user_id == user_id]
        if transaction_type is not None:
            rows = [t for t in rows if t.type == transaction_type]
        rows = sorted(rows, key=lambda t: t.id, reverse=True)
        start = (page - 1) * size
        return rows[start:start + size], len(rows)


class FakeAuctionRepository:
    def __init__(self, rows: dict[int, Auction]) -> None:
        self.rows = rows
        self.filters: dict | None = None

    def add(self, auction: Auction) -> Auction:
        stored = replace(auction, id=max(self.rows, default=0) + 1)
        self.rows[stored.id] = stored
        return stored

    def get(self, auction_id: int) -> Auction | None:
        return self.rows.get(auction_id)

    def lock_for_update(self, auction_id: int) -> Auction | None:
        return self.rows.get(auction_id)

    def list_visible(self, **filters) -> tuple[list[Auction], int]:
        self.filters = filters
        rows = [a for a in self.rows.values() if a.deleted_at is None]
        if filters.get("status") is not None:
            rows = [a for a in rows if a.status == filters["status"]]
        if filters.get("seller_id") is not None:
            rows = [a for a in rows if a.seller_id == filters["seller_id"]]
        if filters.get("category"):
            rows = [a for a in rows if a.category == filters["category"]]
        if filters.get("title_contains"):
            rows = [a for a in rows if filters["title_contains"].lower() in a.title.lower()]
        if filters.get("min_price") is not None:
            rows = [a for a in rows if a.current_price >= filters["min_price"]]
        if filters.get("max_price") is not None:
            rows = [a for a in rows if a.current_price <= filters["max_price"]]
        if filters.get("starts_after") is not None:
            rows = [a for a in rows if a.start_time > filters["starts_after"]]
        if filters.get("starts_before") is not None:
            rows = [a for a in rows if a.start_time <= filters["starts_before"]]
        if filters.get("ends_after") is not None:
            rows = [a for a in rows if a.end_time > filters["ends_after"]]
        if filters.get("ends_before") is not None:
            rows = [a for a in rows if a.end_time <= filters["ends_before"]]
        total = len(rows)
        sort = filters.get("sort", "ending_soon")
        if sort == "ending_soon":
            rows = sorted(rows, key=lambda a: (a.end_time, a.id))
        elif sort == "newest":
            rows = sorted(rows, key=lambda a: (a.start_time, a.id), reverse=True)
        elif sort == "price_asc":
            rows = sorted(rows, key=lambda a: (a.current_price, a.id))
        else:
            rows = sorted(rows, key=lambda a: (a.current_price, a.id), reverse=True)
        start = (filters.get("page", 1) - 1) * filters.get("size", 20)
        size = filters.get("size", 20)
        return rows[start:start + size], total

    def list_for_seller(self, user_id: int, status: str | None, page: int, size: int) -> tuple[list[Auction], int]:
        rows = [a for a in self.rows.values() if a.seller_id == user_id and a.deleted_at is None]
        if status is not None:
            rows = [a for a in rows if a.status == status]
        total = len(rows)
        rows = sorted(rows, key=lambda a: a.id, reverse=True)
        start = (page - 1) * size
        return rows[start:start + size], total

    def mark_deleted(self, auction_id: int, now: datetime) -> None:
        auction = self.rows.get(auction_id)
        if auction is not None:
            self.rows[auction_id] = replace(auction, deleted_at=now)


class FakeUnitOfWork:
    """Works on copies of the tables; only commit() writes them back, like a real transaction."""

    def __init__(self, db: InMemoryDb) -> None:
        self._db = db

    def __enter__(self) -> "FakeUnitOfWork":
        self.users = FakeUserRepository(dict(self._db.users))
        self.wallets = FakeWalletRepository(dict(self._db.wallets), list(self._db.transactions))
        self.auctions = FakeAuctionRepository(dict(self._db.auctions))
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        pass

    def commit(self) -> None:
        self._db.users = self.users.rows
        self._db.wallets = self.wallets.rows
        self._db.auctions = self.auctions.rows
        self._db.transactions = self.wallets.transactions

    def read_only(self) -> None:
        pass


class FakeHasher:
    def __init__(self) -> None:
        self.verify_calls = 0

    def hash(self, plain: str) -> str:
        return "hashed:" + plain

    def verify(self, plain: str, hashed: str) -> bool:
        self.verify_calls += 1
        return hashed == "hashed:" + plain


class FakeTokenService:
    def issue(self, user_id: int, username: str) -> tuple[str, int]:
        return f"token-for-{user_id}", 3600

    def verify(self, token: str) -> int:
        return int(token.removeprefix("token-for-"))


class FixedClock:
    def __init__(self, now: datetime = datetime(2026, 10, 20, 12, 0, tzinfo=UTC)) -> None:
        self.current = now

    def now(self) -> datetime:
        return self.current


class BidsMemoryDb:
    def __init__(self, now):
        self.auctions = {1: SimpleNamespace(
            id=1, seller_id=1, title="Test auction", status="OPEN",
            starting_price=20_000, min_increment=5_000, current_price=20_000,
            bid_count=0, highest_bid_id=None, highest_bidder_id=None,
            start_time=now - timedelta(minutes=1), end_time=now + timedelta(minutes=10),
            extended_count=0, winner_id=None, deleted_at=None,
        )}
        self.wallets = {
            user_id: SimpleNamespace(user_id=user_id, balance=100_000, held=0, updated_at=now)
            for user_id in (1, 2, 3)
        }
        self.bids = []
        self.ledger = []
        self.history_rows = []
        self.history_total = 0
        self.mine_rows = []
        self.mine_total = 0
        self.history_args = None
        self.mine_args = None


class FakeBidsRepository:
    def __init__(self, db):
        self.db = db

    def get_auction(self, auction_id, lock=False):
        auction = self.db.auctions.get(auction_id)
        return auction if auction is not None and auction.deleted_at is None else None

    def lock_wallets(self, user_ids):
        return {user_id: self.db.wallets.get(user_id) for user_id in user_ids}

    def add_bid(self, auction_id, user_id, amount, now):
        bid = SimpleNamespace(id=len(self.db.bids) + 1, auction_id=auction_id,
                              bidder_id=user_id, amount=amount, created_at=now)
        self.db.bids.append(bid)
        return bid

    def add_ledger(self, wallet, kind, delta, auction_id, bid_id, now):
        self.db.ledger.append(dict(
            user_id=wallet.user_id, type=kind, balance_delta=0, held_delta=delta,
            balance_after=wallet.balance, held_after=wallet.held,
            auction_id=auction_id, bid_id=bid_id, created_at=now,
        ))

    def history(self, auction_id, page, size):
        self.db.history_args = (auction_id, page, size)
        return self.db.history_rows, self.db.history_total

    def mine(self, user_id, status, page, size):
        self.db.mine_args = (user_id, status, page, size)
        return self.db.mine_rows, self.db.mine_total


class FakeBidsUnitOfWork:
    def __init__(self, db):
        self.db = db
        self.commits = 0
        self.is_read_only = False

    def __enter__(self):
        self.working = deepcopy(self.db)
        self.bids = FakeBidsRepository(self.working)
        return self

    def __exit__(self, exc_type, exc, tb):
        # Giu tham so truy van de test kiem tra service truyen dung user/filter/page.
        self.db.history_args = self.working.history_args
        self.db.mine_args = self.working.mine_args

    def commit(self):
        self.db.__dict__.update(self.working.__dict__)
        self.commits += 1

    def read_only(self):
        self.is_read_only = True