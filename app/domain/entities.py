from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class User:
    username: str
    password_hash: str
    created_at: datetime
    id: int | None = None


@dataclass(slots=True)
class Wallet:
    user_id: int
    updated_at: datetime
    balance: int = 0
    held: int = 0

    @property
    def available(self) -> int:
        return self.balance - self.held


@dataclass
class Auction:
    """An auction as the business rules see it: plain fields, no database."""

    seller_id: int
    title: str
    description: str
    category: str
    starting_price: int
    min_increment: int
    current_price: int
    bid_count: int
    start_time: datetime
    end_time: datetime
    extended_count: int
    status: str
    created_at: datetime
    id: int | None = None
    reserve_price: int | None = None
    highest_bid_id: int | None = None
    highest_bidder_id: int | None = None
    winner_id: int | None = None
    final_price: int | None = None
    closed_at: datetime | None = None
    deleted_at: datetime | None = None


@dataclass
class Bid:
    auction_id: int
    bidder_id: int
    amount: int
    created_at: datetime
    id: int | None = None


@dataclass
class WalletTransaction:
    """One line of the wallet ledger."""

    user_id: int
    type: str
    balance_delta: int
    held_delta: int
    balance_after: int
    held_after: int
    created_at: datetime
    id: int | None = None
    auction_id: int | None = None
    bid_id: int | None = None
