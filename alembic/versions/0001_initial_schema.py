"""Initial schema: users, rooms and bookings.

Creates the three tables with their indexes, mirroring the SQLAlchemy ORM
in ``app.adapters.persistence.orm``. On PostgreSQL it additionally installs
the ``btree_gist``-backed exclusion constraint that blocks overlapping
bookings for the same room; on any other dialect (e.g. the in-memory SQLite
used by the tests) that step is skipped, matching the previous
``_apply_no_overlap_constraint`` behaviour.

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-07-22

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0001_initial_schema"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

POSTGRES_DIALECT = "postgresql"
NO_OVERLAP_CONSTRAINT = "bookings_no_overlap"

_ENABLE_BTREE_GIST = "CREATE EXTENSION IF NOT EXISTS btree_gist;"
_ADD_NO_OVERLAP_CONSTRAINT = f"""
DO $$
BEGIN
    ALTER TABLE bookings ADD CONSTRAINT {NO_OVERLAP_CONSTRAINT}
        EXCLUDE USING gist (room_code WITH =, tstzrange(starts_at, ends_at) WITH &&);
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;
"""


def upgrade() -> None:
    """Create the schema and, on PostgreSQL, the anti-overlap constraint."""
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("username", sa.String(), nullable=False),
        sa.Column("password_hash", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("username"),
    )
    op.create_table(
        "rooms",
        sa.Column("code", sa.String(), nullable=False),
        sa.Column("capacity", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("code"),
    )
    op.create_table(
        "bookings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("room_code", sa.String(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("attendees", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["room_code"], ["rooms.code"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_bookings_room_code", "bookings", ["room_code"])
    op.create_index("ix_bookings_owner_id", "bookings", ["owner_id"])
    _apply_no_overlap_constraint()


def downgrade() -> None:
    """Drop the schema created by :func:`upgrade`."""
    op.drop_index("ix_bookings_owner_id", table_name="bookings")
    op.drop_index("ix_bookings_room_code", table_name="bookings")
    op.drop_table("bookings")
    op.drop_table("rooms")
    op.drop_table("users")


def _apply_no_overlap_constraint() -> None:
    """Install the PostgreSQL-only exclusion constraint; skip other dialects."""
    if op.get_bind().dialect.name != POSTGRES_DIALECT:
        return
    op.execute(_ENABLE_BTREE_GIST)
    op.execute(_ADD_NO_OVERLAP_CONSTRAINT)
