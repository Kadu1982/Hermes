"""add commands.created_by_device_id for cross-device routing

Revision ID: 0003_command_created_by_device
Revises: 0002_command_notify
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0003_command_created_by_device"
down_revision = "0002_command_notify"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "commands",
        sa.Column("created_by_device_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_commands_created_by_device_id",
        "commands",
        "devices",
        ["created_by_device_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_commands_created_by_device_id", "commands", type_="foreignkey")
    op.drop_column("commands", "created_by_device_id")
