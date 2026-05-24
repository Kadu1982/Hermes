"""add conversation threads and memory events

Revision ID: 0004_memory_threads
Revises: 0003_command_created_by_device
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0004_memory_threads"
down_revision = "0003_command_created_by_device"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "conversation_threads",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("actor_type", sa.String(length=16), nullable=False),
        sa.Column("actor_id", sa.String(length=64), nullable=True),
        sa.Column("origin_channel", sa.String(length=32), nullable=True),
        sa.Column("subject", sa.String(length=200), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("last_intent", sa.String(length=64), nullable=True),
        sa.Column("last_target_device_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("last_command_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["last_target_device_id"], ["devices.id"]),
    )
    op.create_index("ix_conversation_threads_actor_type", "conversation_threads", ["actor_type"], unique=False)
    op.create_index("ix_conversation_threads_actor_id", "conversation_threads", ["actor_id"], unique=False)

    op.add_column("commands", sa.Column("thread_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        "fk_commands_thread_id",
        "commands",
        "conversation_threads",
        ["thread_id"],
        ["id"],
    )

    op.create_table(
        "memory_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("thread_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("command_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("kind", sa.String(length=48), nullable=False),
        sa.Column("payload", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["thread_id"], ["conversation_threads.id"]),
        sa.ForeignKeyConstraint(["command_id"], ["commands.id"]),
    )
    op.create_index("ix_memory_events_thread_id", "memory_events", ["thread_id"], unique=False)

    op.create_foreign_key(
        "fk_conversation_threads_last_command_id",
        "conversation_threads",
        "commands",
        ["last_command_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_conversation_threads_last_command_id", "conversation_threads", type_="foreignkey")
    op.drop_index("ix_memory_events_thread_id", table_name="memory_events")
    op.drop_table("memory_events")
    op.drop_constraint("fk_commands_thread_id", "commands", type_="foreignkey")
    op.drop_column("commands", "thread_id")
    op.drop_index("ix_conversation_threads_actor_id", table_name="conversation_threads")
    op.drop_index("ix_conversation_threads_actor_type", table_name="conversation_threads")
    op.drop_table("conversation_threads")
