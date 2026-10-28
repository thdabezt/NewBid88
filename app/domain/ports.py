"""Interfaces the services layer depends on. infra implements them; main.py wires them in."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Protocol, Any

from app.domain.entities import User, Wallet


class UserRepository(Protocol):
    def add(self, user: User) -> User:
        """Insert the user and return it with its id. Raises UsernameTaken if the username exists."""
        ...

    def get(self, id: int) -> User | None: ...

    def get_by_username(self, username: str) -> User | None: ...


class WalletRepository(Protocol):
    def add(self, wallet: Wallet) -> None: ...


class AuctionRepository(Protocol):
    def add(self, auction: Any) -> Any: ...

    def get(self, auction_id: int, lock: bool = False) -> Any | None: ...

    def list(
        self,
        *,
        state: str,
        now: datetime,
        q: str | None,
        category: str | None,
        seller_id: int | None,
        min_price: int | None,
        max_price: int | None,
        sort: str,
        page: int,
        size: int,
    ) -> tuple[list[Any], int]: ...

    def list_for_seller(
        self,
        seller_id: int,
        status: str | None,
        page: int,
        size: int,
    ) -> tuple[list[Any], int]: ...

    def delete(self, auction: Any, deleted_at: datetime) -> None: ...


class UnitOfWork(Protocol):
    """One transaction. Leaving the with-block without commit() rolls everything back."""

    users: UserRepository
    wallets: WalletRepository
    auctions: AuctionRepository

    def __enter__(self) -> "UnitOfWork": ...

    def __exit__(self, exc_type, exc, tb) -> None: ...

    def commit(self) -> None: ...

    def read_only(self) -> None: ...


UnitOfWorkFactory = Callable[[], UnitOfWork]


class PasswordHasher(Protocol):
    def hash(self, plain: str) -> str: ...

    def verify(self, plain: str, hashed: str) -> bool: ...


class TokenService(Protocol):
    def issue(self, user_id: int, username: str) -> tuple[str, int]:
        """Return the access token and its lifetime in seconds."""
        ...

    def verify(self, token: str) -> int:
        """Return the user id in the token. Raises InvalidToken."""
        ...


class Clock(Protocol):
    def now(self) -> datetime:
        """Current time, timezone-aware UTC."""
        ...
