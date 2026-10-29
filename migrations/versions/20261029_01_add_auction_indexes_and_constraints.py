"""align auction schema with the database specification

Revision ID: 20261029_01
Revises: 20261025_01
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20261029_01"
down_revision: Union[str, Sequence[str], None] = "20261025_01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "auctions",
        "status",
        existing_type=sa.String(length=20),
        type_=sa.String(length=10),
        existing_nullable=False,
        existing_server_default=sa.text("'OPEN'"),
    )
    op.create_foreign_key(
        "fk_wallets_user_id_users",
        "wallets",
        "users",
        ["user_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_wallet_transactions_user_id_users",
        "wallet_transactions",
        "users",
        ["user_id"],
        ["id"],
    )
    op.create_index(
        "ix_auctions_status_end_time_open",
        "auctions",
        ["status", "end_time"],
        postgresql_where=sa.text("status = 'OPEN'"),
    )
    op.create_index(
        "ix_auctions_seller_id_id",
        "auctions",
        ["seller_id", sa.text("id DESC")],
    )
    op.create_index("ix_auctions_category", "auctions", ["category"])


def downgrade() -> None:
    op.drop_index("ix_auctions_category", table_name="auctions")
    op.drop_index("ix_auctions_seller_id_id", table_name="auctions")
    op.drop_index("ix_auctions_status_end_time_open", table_name="auctions")
    op.drop_constraint(
        "fk_wallet_transactions_user_id_users",
        "wallet_transactions",
        type_="foreignkey",
    )
    op.drop_constraint("fk_wallets_user_id_users", "wallets", type_="foreignkey")
    op.alter_column(
        "auctions",
        "status",
        existing_type=sa.String(length=10),
        type_=sa.String(length=20),
        existing_nullable=False,
        existing_server_default=sa.text("'OPEN'"),
    )
