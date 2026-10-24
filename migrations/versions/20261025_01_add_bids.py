"""add bids and link auctions to highest bids

Revision ID: 20261024_03
Revises: 20261024_02
"""

from alembic import op
import sqlalchemy as sa

revision = "20261025_01"
down_revision = "20261024_02"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "bids",
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("auction_id", sa.BigInteger(), nullable=False),
        sa.Column("bidder_id", sa.BigInteger(), nullable=False),
        sa.Column("amount", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_bids"),
        sa.ForeignKeyConstraint(["auction_id"], ["auctions.id"], name="fk_bids_auction_id_auctions"),
        sa.ForeignKeyConstraint(["bidder_id"], ["users.id"], name="fk_bids_bidder_id_users"),
        sa.UniqueConstraint("auction_id", "amount", name="uq_bids_auction_id_amount"),
    )

    op.create_index("ix_bids_auction_id_id", "bids", ["auction_id", sa.text("id DESC")])
    op.create_index("ix_bids_bidder_id_auction_id", "bids", ["bidder_id", "auction_id"])

    op.create_foreign_key("fk_auctions_highest_bid_id_bids", "auctions", "bids", ["highest_bid_id"], ["id"])


def downgrade() -> None:
    op.drop_constraint("fk_auctions_highest_bid_id_bids", "auctions", type_="foreignkey")
    op.drop_table("bids")