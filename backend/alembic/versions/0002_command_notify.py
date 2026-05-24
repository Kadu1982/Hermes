"""command notify and natural source

Revision ID: 0002_command_notify
Revises: 0001_initial
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0002_command_notify"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("commands", sa.Column("notify_channel", sa.String(length=32), nullable=True))
    op.add_column("commands", sa.Column("notify_on", sa.String(length=16), nullable=True))
    op.add_column("commands", sa.Column("source_text", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("commands", "source_text")
    op.drop_column("commands", "notify_on")
    op.drop_column("commands", "notify_channel")
