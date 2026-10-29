"""add user credentials

Revision ID: 20261024_02
Revises: 20261024_01
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20261024_02"
down_revision: Union[str, Sequence[str], None] = "20261024_01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("password_hash", sa.String(length=60), server_default="", nullable=False))
    op.alter_column("users", "password_hash", server_default=None)
    op.add_column(
        "users",
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_column("users", "created_at")
    op.drop_column("users", "password_hash")
