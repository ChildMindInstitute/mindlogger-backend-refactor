"""add answer group

Revision ID: 8953aa43e382
Revises: f681621bf85d
Create Date: 2023-04-11 13:06:19.960723

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "016848d34c04"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "answers",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=True),
        sa.Column("applet_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("version", sa.Text(), nullable=True),
        sa.Column("submit_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("client", sa.JSON(), nullable=True),
        sa.Column("applet_history_id", sa.Text(), nullable=False),
        sa.Column("flow_history_id", sa.Text(), nullable=True),
        sa.Column("activity_history_id", sa.Text(), nullable=False),
        sa.Column(
            "respondent_id", postgresql.UUID(as_uuid=True), nullable=True
        ),
        sa.Column("migrated_date", sa.DateTime(), nullable=True),
        sa.Column("migrated_updated", sa.DateTime(), nullable=True),
        sa.Column("is_flow_completed", sa.Boolean(), nullable=True),
        sa.Column(
            "migrated_data",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        op.f("ix_answers_applet_history_id"),
        "answers",
        ["applet_history_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_answers_activity_history_id"),
        "answers",
        ["activity_history_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_answers_respondent_id"),
        "answers",
        ["respondent_id"],
        unique=False,
    )

    op.create_table(
        "answers_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=True),
        sa.Column("answer_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "respondent_id", postgresql.UUID(as_uuid=True), nullable=True
        ),
        sa.Column("answer", sa.Text(), nullable=True),
        sa.Column("events", sa.Text(), nullable=True),
        sa.Column("item_ids", sa.JSON(), nullable=True),
        sa.Column("identifier", sa.Text(), nullable=True),
        sa.Column("user_public_key", sa.Text(), nullable=True),
        sa.Column("scheduled_datetime", sa.DateTime(), nullable=True),
        sa.Column("start_datetime", sa.DateTime(), nullable=False),
        sa.Column("end_datetime", sa.DateTime(), nullable=False),
        sa.Column("is_assessment", sa.Boolean(), nullable=True),
        sa.Column("scheduled_event_id", sa.Text(), nullable=True),
        sa.Column("local_end_date", sa.Date(), nullable=True),
        sa.Column("local_end_time", sa.Time(), nullable=True),
        sa.Column("migrated_date", sa.DateTime(), nullable=True),
        sa.Column("migrated_updated", sa.DateTime(), nullable=True),
        sa.Column(
            "migrated_data",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["answer_id"],
            ["answers.id"],
            ondelete="CASCADE",
            name="fk_answers_items_answer_id",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_answers_items_answer_id"),
        "answers_items",
        ["answer_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_answers_items_respondent_id"),
        "answers_items",
        ["respondent_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_answers_items_local_end_date"),
        "answers_items",
        ["local_end_date"],
        unique=False,
    )


def downgrade():
    op.drop_table("answers_items")
    op.drop_table("answers")
