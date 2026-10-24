from dataclasses import dataclass
from datetime import datetime


@dataclass
class User:
    username: str
    password_hash: str
    created_at: datetime
    id: int | None = None


@dataclass
class Wallet:
    """held is the money locked by the user's leading bids; available is what they can still bid with."""

    user_id: int
    updated_at: datetime
    balance: int = 0
    held: int = 0

    @property
    def available(self) -> int:
        return self.balance - self.held
