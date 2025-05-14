"""Add answers_ehr table

Revision ID: 9b882445f218
Revises: 2a9ee1cea9c6
Create Date: 2025-04-29 16:50:37.173174

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "9b882445f218"
down_revision = "2a9ee1cea9c6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "answers_ehr",
        sa.Column("is_deleted", sa.Boolean(), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("timezone('utc', now())"), nullable=True),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("timezone('utc', now())"), nullable=True),
        sa.Column("migrated_date", sa.DateTime(), nullable=True),
        sa.Column("migrated_updated", sa.DateTime(), nullable=True),
        sa.Column("submit_id", postgresql.UUID(as_uuid=True)),
        sa.Column("activity_id", postgresql.UUID(as_uuid=True)),
        sa.Column("ehr_storage_uri", sa.Text(), nullable=True),
        sa.Column("ehr_ingestion_status", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_answers_ehr")),
    )
    op.create_index(
        op.f("ix_answers_ehr_submit_activity_id"), "answers_ehr", ["submit_id", "activity_id"], unique=False
    )
    op.create_unique_constraint("answers_ehr_submit_activity_key", "answers_ehr", ["submit_id", "activity_id"])


def downgrade() -> None:
    op.drop_constraint("answers_ehr_submit_activity_key", "answers_ehr", type_="unique")
    op.drop_index(op.f("ix_answers_ehr_submit_activity_id"), table_name="answers_ehr")
    op.drop_table("answers_ehr")
