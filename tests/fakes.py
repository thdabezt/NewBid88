"""In-memory stand-ins for the domain ports, for tests that should not need PostgreSQL."""

from dataclasses import replace
from datetime import UTC, datetime

from app.domain.entities import User, Wallet
from app.domain.errors import UsernameTaken


class InMemoryDb:
    def __init__(self) -> None:
        self.users: dict[int, User] = {}
        self.wallets: dict[int, Wallet] = {}


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


class FakeWalletRepository:
    def __init__(self, rows: dict[int, Wallet]) -> None:
        self.rows = rows

    def add(self, wallet: Wallet) -> None:
        self.rows[wallet.user_id] = wallet


class FakeUnitOfWork:
    """Works on copies of the tables; only commit() writes them back, like a real transaction."""

    def __init__(self, db: InMemoryDb) -> None:
        self._db = db

    def __enter__(self) -> "FakeUnitOfWork":
        self.users = FakeUserRepository(dict(self._db.users))
        self.wallets = FakeWalletRepository(dict(self._db.wallets))
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        pass

    def commit(self) -> None:
        self._db.users = self.users.rows
        self._db.wallets = self.wallets.rows


class FakeHasher:
    def __init__(self) -> None:
        self.verify_calls = 0

    def hash(self, plain: str) -> str:
        return "hashed:" + plain

    def verify(self, plain: str, hashed: str) -> bool:
        self.verify_calls += 1
        return hashed == "hashed:" + plain


class FixedClock:
    def __init__(self, now: datetime = datetime(2026, 10, 20, 12, 0, tzinfo=UTC)) -> None:
        self.current = now

    def now(self) -> datetime:
        return self.current
