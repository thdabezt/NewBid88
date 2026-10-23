from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, DateTime, Identity, Index, MetaData, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

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

    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    balance: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    held: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class WalletTransaction(Base):
    __tablename__ = "wallet_transactions"
    __table_args__ = (Index("ix_wallet_transactions_user_id_id", "user_id", "id"),)

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
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
