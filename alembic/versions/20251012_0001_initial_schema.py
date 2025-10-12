"""Initial Kv and memory event tables

Revision ID: 20251012_0001
Revises:
Create Date: 2025-10-12 00:00:00

"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "20251012_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "kv_store",
        sa.Column("key", sa.Text(), primary_key=True),
        sa.Column("value", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    )

    op.create_table(
        "memory_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("namespace", sa.Text(), nullable=False),
        sa.Column("type", sa.Text(), nullable=False),
        sa.Column("timestamp", sa.Float(precision=53), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    )
    op.create_index(
        "ix_memory_events_namespace_timestamp",
        "memory_events",
        ["namespace", "timestamp"],
        unique=False,
    )
    op.create_index(
        "ix_memory_events_event_id",
        "memory_events",
        ["event_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_memory_events_event_id", table_name="memory_events")
    op.drop_index("ix_memory_events_namespace_timestamp", table_name="memory_events")
    op.drop_table("memory_events")
    op.drop_table("kv_store")
