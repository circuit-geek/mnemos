"""add per-video requested and tracked concepts

Revision ID: 0002
Revises: 0001
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0002"
down_revision = "0001"


def upgrade() -> None:
    json_type = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")
    op.add_column("videos", sa.Column("requested_concepts", json_type, nullable=True))
    op.add_column("videos", sa.Column("tracked_concepts", json_type, nullable=True))


def downgrade() -> None:
    op.drop_column("videos", "tracked_concepts")
    op.drop_column("videos", "requested_concepts")
