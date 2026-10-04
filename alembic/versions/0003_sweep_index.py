"""partial index for expiry sweeper

Revision ID: 0003
Revises: 0002
"""
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_tickets_sweep "
        "ON tickets (reserved_at) WHERE status='reserved'"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_tickets_sweep")
