"""Interfaces the services layer depends on. infra implements them; main.py wires them in."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Protocol

from app.domain.entities import Auction, User, Wallet, WalletTransaction


class UserRepository(Protocol):
    def add(self, user: User) -> User:
        """Insert the user and return it with its id. Raises UsernameTaken if the username exists."""
        ...

    def get(self, id: int) -> User | None: ...

    def get_by_username(self, username: str) -> User | None: ...

    def get_many(self, ids: list[int]) -> dict[int, User]:
        """Return the users found, keyed by id. Missing ids are simply absent."""
        ...


class WalletRepository(Protocol):
    def add(self, wallet: Wallet) -> None: ...

    def get(self, user_id: int) -> Wallet | None: ...

    def credit(self, user_id: int, amount: int, now: datetime) -> tuple[WalletTransaction, Wallet]:
        """Add money to the wallet and write the ledger row. Raises NotFoundError if there is no wallet."""
        ...

    def list_transactions(
        self, user_id: int, transaction_type: str | None, page: int, size: int
    ) -> tuple[list[WalletTransaction], int]:
        """Return one page of ledger rows, newest first, plus the total count."""
        ...


class AuctionRepository(Protocol):
    def add(self, auction: Auction) -> Auction:
        """Insert the auction and return it with its id."""
        ...

    def get(self, auction_id: int) -> Auction | None:
        """Return the auction, deleted ones included."""
        ...

    def lock_for_update(self, auction_id: int) -> Auction | None:
        """Return the auction with a row lock held until the transaction ends."""
        ...

    def list_visible(self, **filters) -> tuple[list[Auction], int]:
        """Return one page of auctions that are not deleted, plus the total count."""
        ...

    def list_for_seller(self, user_id: int, status: str | None, page: int, size: int) -> tuple[list[Auction], int]:
        """Return one page of a seller's auctions, plus the total count."""
        ...

    def mark_deleted(self, auction_id: int, now: datetime) -> None: ...


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
