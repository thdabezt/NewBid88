"""Interfaces the services layer depends on. infra implements them; main.py wires them in."""

from collections.abc import Callable
from datetime import datetime
from typing import Protocol

from app.domain.entities import User, Wallet


class UserRepository(Protocol):
    def add(self, user: User) -> User:
        """Insert the user and return it with its id. Raises UsernameTaken if the username exists."""
        ...

    def get(self, id: int) -> User | None: ...

    def get_by_username(self, username: str) -> User | None: ...


class WalletRepository(Protocol):
    def add(self, wallet: Wallet) -> None: ...


class UnitOfWork(Protocol):
    """One transaction. Leaving the with-block without commit() rolls everything back."""

    users: UserRepository
    wallets: WalletRepository

    def __enter__(self) -> "UnitOfWork": ...

    def __exit__(self, exc_type, exc, tb) -> None: ...

    def commit(self) -> None: ...


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
