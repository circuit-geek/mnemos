"""job stage reporting and video frame size

Revision ID: 0003
Revises: 0002
"""

import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"


def upgrade() -> None:
    op.add_column("videos", sa.Column("width", sa.Integer(), nullable=True))
    op.add_column("videos", sa.Column("height", sa.Integer(), nullable=True))
    op.add_column("processing_jobs", sa.Column("stage", sa.String(length=32), nullable=True))
    op.add_column("processing_jobs", sa.Column("stage_detail", sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column("processing_jobs", "stage_detail")
    op.drop_column("processing_jobs", "stage")
    op.drop_column("videos", "height")
    op.drop_column("videos", "width")
