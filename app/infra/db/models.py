from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, DateTime, Identity, Index, MetaData, String, desc, func, Text, Integer, ForeignKey, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import UniqueConstraint

# Fixed constraint names so Alembic migrations stay stable.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Parent class of every table model."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class Wallet(Base):
    __tablename__ = "wallets"
    __table_args__ = (
        CheckConstraint("balance >= 0", name="balance_nonnegative"),
        CheckConstraint("held >= 0 AND held <= balance", name="held_within_balance"),
    )

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    balance: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    held: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class WalletTransaction(Base):
    __tablename__ = "wallet_transactions"
    __table_args__ = (Index("ix_wallet_transactions_user_id_id", "user_id", "id"),)

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    type: Mapped[str] = mapped_column(String(30), nullable=False)
    balance_delta: Mapped[int] = mapped_column(BigInteger, nullable=False)
    held_delta: Mapped[int] = mapped_column(BigInteger, nullable=False)
    balance_after: Mapped[int] = mapped_column(BigInteger, nullable=False)
    held_after: Mapped[int] = mapped_column(BigInteger, nullable=False)
    auction_id: Mapped[int | None] = mapped_column(BigInteger)
    bid_id: Mapped[int | None] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    username: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String(60), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class Auction(Base):
    __tablename__ = "auctions"
    __table_args__ = (
        CheckConstraint("starting_price >= 0", name="starting_price_nonnegative"),
        CheckConstraint("current_price >= 0", name="current_price_nonnegative"),
        CheckConstraint("bid_count >= 0", name="bid_count_nonnegative"),
        CheckConstraint("end_time > start_time", name="valid_time_range"),
        CheckConstraint("reserve_price IS NULL OR reserve_price >= starting_price", name="reserve_not_below_start"),
        CheckConstraint("status IN ('OPEN', 'SOLD', 'UNSOLD')", name="valid_status"),
        CheckConstraint("min_increment > 0", name="min_increment_positive"),
        Index(
            "ix_auctions_status_end_time_open",
            "status",
            "end_time",
            postgresql_where=text("status = 'OPEN'"),
        ),
        Index("ix_auctions_seller_id_id", "seller_id", desc("id")),
        Index("ix_auctions_category", "category"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    seller_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    starting_price: Mapped[int] = mapped_column(BigInteger, nullable=False)
    min_increment: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=1_000, server_default="1000"
    )
    reserve_price: Mapped[int | None] = mapped_column(BigInteger)
    current_price: Mapped[int] = mapped_column(BigInteger, nullable=False)
    bid_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    highest_bid_id: Mapped[int | None] = mapped_column(ForeignKey("bids.id"), nullable=True)
    highest_bidder_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    extended_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    status: Mapped[str] = mapped_column(String(10), nullable=False, default="OPEN", server_default="OPEN")
    winner_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    final_price: Mapped[int | None] = mapped_column(BigInteger)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

class Bid(Base):
    __tablename__ = "bids"
    __table_args__ = (
        UniqueConstraint("auction_id", "amount", name="uq_bids_auction_id_amount"),
        Index("ix_bids_bidder_id_auction_id", "bidder_id", "auction_id"),
        Index("ix_bids_auction_id_id", "auction_id", desc("id")),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    auction_id: Mapped[int] = mapped_column(ForeignKey("auctions.id"), nullable=False)
    bidder_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    amount: Mapped[int] = mapped_column(BigInteger, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())