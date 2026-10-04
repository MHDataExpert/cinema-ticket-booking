"""initial tables + indexes

Revision ID: 0001
Revises:
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

status_enum = postgresql.ENUM("available", "reserved", "booked", name="ticket_status", create_type=False)


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    status_enum.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "venues",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("city", sa.String(255), nullable=False),
        sa.Column("address", sa.String(512), nullable=False),
        sa.Column("capacity", sa.Integer(), nullable=False),
        sa.Column("seat_map", sa.JSON(), nullable=False),
    )
    op.create_index("ix_venues_city", "venues", ["city"])
    op.create_table(
        "performers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("kind", sa.String(50), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
    )
    op.create_table(
        "events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("starts_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("venue_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("venues.id"), nullable=False),
        sa.Column("performer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("performers.id"), nullable=False),
    )
    op.create_index("ix_events_event_type", "events", ["event_type"])
    op.create_index("ix_events_starts_at", "events", ["starts_at"])
    op.execute("CREATE INDEX ix_events_name_trgm ON events USING gin (name gin_trgm_ops)")
    op.create_table(
        "tickets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("events.id"), nullable=False),
        sa.Column("section", sa.String(100), nullable=False),
        sa.Column("seat", sa.String(50), nullable=False),
        sa.Column("price", sa.Numeric(10, 2), nullable=False),
        sa.Column("status", status_enum, server_default="available", nullable=False),
        sa.Column("reserved_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("user_id", sa.Text(), nullable=True),
    )
    op.create_index("ix_tickets_event_id", "tickets", ["event_id"])
    op.create_index("ix_tickets_event_status", "tickets", ["event_id", "status"])


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_tickets_event_status")
    op.execute("DROP INDEX IF EXISTS ix_tickets_event_id")
    op.drop_table("tickets")
    op.execute("DROP INDEX IF EXISTS ix_events_name_trgm")
    op.drop_index("ix_events_starts_at")
    op.drop_index("ix_events_event_type")
    op.drop_table("events")
    op.drop_table("performers")
    op.drop_index("ix_venues_city")
    op.drop_table("venues")
    status_enum.drop(op.get_bind(), checkfirst=True)
