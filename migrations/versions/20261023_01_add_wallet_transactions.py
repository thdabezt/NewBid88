"""add wallet transactions

Revision ID: 20261023_01
Revises:
Create Date: 2026-10-23

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20261023_01"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "wallets",
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("balance", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("held", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("balance >= 0", name="ck_wallets_balance_nonnegative"),
        sa.CheckConstraint("held >= 0 AND held <= balance", name="ck_wallets_held_within_balance"),
        sa.PrimaryKeyConstraint("user_id", name="pk_wallets"),
    )
    op.create_table(
        "wallet_transactions",
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("type", sa.String(length=30), nullable=False),
        sa.Column("balance_delta", sa.BigInteger(), nullable=False),
        sa.Column("held_delta", sa.BigInteger(), nullable=False),
        sa.Column("balance_after", sa.BigInteger(), nullable=False),
        sa.Column("held_after", sa.BigInteger(), nullable=False),
        sa.Column("auction_id", sa.BigInteger(), nullable=True),
        sa.Column("bid_id", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_wallet_transactions"),
    )
    op.create_index(
        "ix_wallet_transactions_user_id_id",
        "wallet_transactions",
        ["user_id", "id"],
    )


def downgrade() -> None:
    op.drop_index("ix_wallet_transactions_user_id_id", table_name="wallet_transactions")
    op.drop_table("wallet_transactions")
    op.drop_table("wallets")
