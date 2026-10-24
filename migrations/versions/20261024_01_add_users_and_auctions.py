"""add users and auctions

Revision ID: 20261024_01
Revises: 20261023_01
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20261024_01"
down_revision: Union[str, Sequence[str], None] = "20261023_01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("username", sa.String(length=50), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
        sa.UniqueConstraint("username", name="uq_users_username"),
    )
    op.create_table(
        "auctions",
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("seller_id", sa.BigInteger(), nullable=False),
        sa.Column("title", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), server_default="", nullable=False),
        sa.Column("category", sa.String(length=50), nullable=False),
        sa.Column("starting_price", sa.BigInteger(), nullable=False),
        sa.Column("min_increment", sa.BigInteger(), server_default="1000", nullable=False),
        sa.Column("reserve_price", sa.BigInteger(), nullable=True),
        sa.Column("current_price", sa.BigInteger(), nullable=False),
        sa.Column("bid_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("highest_bid_id", sa.BigInteger(), nullable=True),
        sa.Column("highest_bidder_id", sa.BigInteger(), nullable=True),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("extended_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("status", sa.String(length=20), server_default="OPEN", nullable=False),
        sa.Column("winner_id", sa.BigInteger(), nullable=True),
        sa.Column("final_price", sa.BigInteger(), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("starting_price >= 0", name="ck_auctions_starting_price_nonnegative"),
        sa.CheckConstraint("current_price >= 0", name="ck_auctions_current_price_nonnegative"),
        sa.CheckConstraint("bid_count >= 0", name="ck_auctions_bid_count_nonnegative"),
        sa.CheckConstraint("end_time > start_time", name="ck_auctions_valid_time_range"),
        sa.CheckConstraint(
            "reserve_price IS NULL OR reserve_price >= starting_price",
            name="ck_auctions_reserve_not_below_start",
        ),
        sa.CheckConstraint(
            "status IN ('OPEN', 'SOLD', 'UNSOLD')",
            name="ck_auctions_valid_status",
        ),
        sa.CheckConstraint("min_increment > 0", name="ck_auctions_min_increment_positive"),
        sa.ForeignKeyConstraint(["seller_id"], ["users.id"], name="fk_auctions_seller_id_users"),
        sa.ForeignKeyConstraint(
            ["highest_bidder_id"], ["users.id"], name="fk_auctions_highest_bidder_id_users"
        ),
        sa.ForeignKeyConstraint(["winner_id"], ["users.id"], name="fk_auctions_winner_id_users"),
        sa.PrimaryKeyConstraint("id", name="pk_auctions"),
    )


def downgrade() -> None:
    op.drop_table("auctions")
    op.drop_table("users")
