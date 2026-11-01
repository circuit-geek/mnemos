"""content hash for upload de-duplication

Revision ID: 0004
Revises: 0003
"""

import sqlalchemy as sa
from alembic import op

revision = "0004"
down_revision = "0003"


def upgrade() -> None:
    op.add_column("videos", sa.Column("content_hash", sa.String(length=64), nullable=True))
    op.create_index(op.f("ix_videos_content_hash"), "videos", ["content_hash"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_videos_content_hash"), table_name="videos")
    op.drop_column("videos", "content_hash")
