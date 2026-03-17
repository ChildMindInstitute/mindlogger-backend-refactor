"""Add missing migrations

Revision ID: 8c88d334aba6
Revises: e6728c9ce215
Create Date: 2026-03-04 15:19:19.964617

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "8c88d334aba6"
down_revision = "e6728c9ce215"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add missing values to token_blacklist.type enum
    op.execute(sa.text("ALTER TYPE token_purpose ADD VALUE IF NOT EXISTS 'MFA'"))
    op.execute(sa.text("ALTER TYPE token_purpose ADD VALUE IF NOT EXISTS 'DOWNLOAD_RECOVERY_CODES'"))

    # Drop obsolete applet_events_cleanup table (left by applet_events cleanup)
    op.drop_table("applet_events_cleanup")

    # Drop orphan *_events tables (left by migration to events table)
    op.drop_constraint("fk_activity_events_event_id_events", "activity_events", type_="foreignkey")
    op.drop_constraint("fk_flow_events_event_id_events", "flow_events", type_="foreignkey")
    op.drop_constraint("fk_user_events_event_id_events", "user_events", type_="foreignkey")
    op.drop_constraint("fk_user_events_user_id_users", "user_events", type_="foreignkey")
    op.drop_table("activity_events")
    op.drop_table("flow_events")
    op.drop_table("user_events")

    # Drop orphan periodicity table (left by migration to events table)
    op.drop_table("periodicity")

    # Drop orphan columns
    op.drop_column("events", "periodicity_id")
    op.drop_column("subjects", "is_deleted_null")

    # Drop redundant index on answers_ehr (already indexed by answers_ehr_submit_activity_key unique constraint)
    op.drop_index("ix_answers_ehr_submit_activity_id", table_name="answers_ehr")

    # Create missing consents table (defined for LORIS integration)
    op.create_table(
        "consents",
        sa.Column("is_deleted", sa.Boolean(), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("timezone('utc', now())"), nullable=True),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("timezone('utc', now())"), nullable=True),
        sa.Column("migrated_date", sa.DateTime(), nullable=True),
        sa.Column("migrated_updated", sa.DateTime(), nullable=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("is_ready_share_data", sa.Boolean(), nullable=True),
        sa.Column("is_ready_share_media_data", sa.Boolean(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_consents_user_id_users"), ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_consents")),
    )


def downgrade() -> None:
    # Drop missing consents table
    op.drop_table("consents")

    # Restore redundant index on answers_ehr
    op.create_index("ix_answers_ehr_submit_activity_id", "answers_ehr", ["submit_id", "activity_id"], unique=False)

    # Restore orphan columns
    op.add_column("subjects", sa.Column("is_deleted_null", sa.Boolean(), server_default=sa.text("false"), nullable=False))
    op.add_column("events", sa.Column("periodicity_id", postgresql.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False))

    # Restore orphan periodicity table
    op.create_table(
        "periodicity",
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=True),
        sa.Column("type", sa.String(length=10), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("selected_date", sa.Date(), nullable=True),
        sa.Column("id", postgresql.UUID(), nullable=False),
        sa.Column("migrated_date", sa.DateTime(), nullable=True),
        sa.Column("migrated_updated", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_periodicity")),
    )

    # Restore orphan *_events tables
    op.create_table(
        "activity_events",
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=True),
        sa.Column("id", postgresql.UUID(), nullable=False),
        sa.Column("activity_id", postgresql.UUID(), nullable=False),
        sa.Column("event_id", postgresql.UUID(), nullable=False),
        sa.Column("migrated_date", sa.DateTime(), nullable=True),
        sa.Column("migrated_updated", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], name="fk_activity_events_event_id_events", onupdate="CASCADE", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_activity_events")),
        sa.UniqueConstraint("activity_id", "event_id", "is_deleted", name="_unique_activity_events"),
    )
    op.create_table(
        "flow_events",
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=True),
        sa.Column("id", postgresql.UUID(), nullable=False),
        sa.Column("flow_id", postgresql.UUID(), nullable=False),
        sa.Column("event_id", postgresql.UUID(), nullable=False),
        sa.Column("migrated_date", sa.DateTime(), nullable=True),
        sa.Column("migrated_updated", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], name="fk_flow_events_event_id_events", onupdate="CASCADE", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_flow_events")),
        sa.UniqueConstraint("flow_id", "event_id", "is_deleted", name="_unique_flow_events"),
    )
    op.create_table(
        "user_events",
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=True),
        sa.Column("id", postgresql.UUID(), nullable=False),
        sa.Column("user_id", postgresql.UUID(), nullable=False),
        sa.Column("event_id", postgresql.UUID(), nullable=False),
        sa.Column("migrated_date", sa.DateTime(), nullable=True),
        sa.Column("migrated_updated", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], name="fk_user_events_event_id_events", onupdate="CASCADE", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_user_events_user_id_users", ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_user_events")),
        sa.UniqueConstraint("user_id", "event_id", "is_deleted", name="_unique_user_events"),
    )

    # Restore obsolete applet_events_cleanup table
    op.create_table(
        "applet_events_cleanup",
        sa.Column("is_deleted", sa.Boolean(), nullable=True),
        sa.Column("id", postgresql.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("migrated_date", sa.DateTime(), nullable=True),
        sa.Column("migrated_updated", sa.DateTime(), nullable=True),
        sa.Column("applet_id", sa.String(), nullable=False),
        sa.Column("event_id", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_applet_events_cleanup")),
        sa.UniqueConstraint("applet_id", "event_id", "is_deleted", name=op.f("_unique_applet_events_cleanup")),
    )

    # Remove missing values from token_blacklist.type enum (recreate because PostgreSQL cannot remove enum values)
    op.execute(sa.text("ALTER TYPE token_purpose RENAME TO token_purpose_old"))
    op.execute(sa.text("CREATE TYPE token_purpose AS ENUM ('ACCESS', 'REFRESH')"))
    op.execute(sa.text("ALTER TABLE token_blacklist ALTER COLUMN type TYPE token_purpose USING type::text::token_purpose"))
    op.execute(sa.text("DROP TYPE token_purpose_old"))
