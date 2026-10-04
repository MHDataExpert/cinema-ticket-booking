"""movie director/year on performers

Revision ID: 0002
Revises: 0001
"""

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("performers", sa.Column("director", sa.Text(), nullable=False, server_default=""))
    op.add_column("performers", sa.Column("year", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("performers", "year")
    op.drop_column("performers", "director")
