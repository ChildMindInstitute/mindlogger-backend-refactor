"""create audit_logs table

Revision ID: f475633a2836
Revises: 8c88d334aba6
Create Date: 2026-06-17 15:47:36.654683

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "f475633a2836"
down_revision = "8c88d334aba6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("timezone('utc', now())"), nullable=True),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("timezone('utc', now())"), nullable=True),
        sa.Column("migrated_date", sa.DateTime(), nullable=True),
        sa.Column("migrated_updated", sa.DateTime(), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=True),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_timestamp", sa.DateTime(), nullable=False),
        sa.Column("event_action", sa.String(), nullable=False),
        sa.Column("event_outcome", sa.String(), nullable=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("applet_ids", postgresql.ARRAY(postgresql.UUID(as_uuid=True)), nullable=True),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_audit_logs")),
        sa.UniqueConstraint("event_id", name=op.f("uq_audit_logs_event_id")),
    )
    op.create_index(op.f("ix_audit_logs_user_id"), "audit_logs", ["user_id"], unique=False)
    op.create_index(
        "ix_audit_logs_event_timestamp_event_id",
        "audit_logs",
        ["event_timestamp", "event_id"],
        unique=False,
    )
    op.create_index(
        "ix_audit_logs_applet_ids",
        "audit_logs",
        ["applet_ids"],
        unique=False,
        postgresql_using="gin",
    )


def downgrade() -> None:
    op.drop_index("ix_audit_logs_applet_ids", table_name="audit_logs", postgresql_using="gin")
    op.drop_index("ix_audit_logs_event_timestamp_event_id", table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_user_id"), table_name="audit_logs")
    op.drop_table("audit_logs")
