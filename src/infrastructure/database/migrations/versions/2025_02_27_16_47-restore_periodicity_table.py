"""Restore periodicity table

Revision ID: 8fa31d7d9831
Revises: 70987d489b17
Create Date: 2025-02-27 16:47:39.684727

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "8fa31d7d9831"
down_revision = "70987d489b17"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Recreate the periodicity table
    op.create_table(
        "periodicity",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("timezone('utc', now())"), nullable=True),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("timezone('utc', now())"), nullable=True),
        sa.Column("migrated_date", sa.DateTime(), nullable=True),
        sa.Column("migrated_updated", sa.DateTime(), nullable=True),
        sa.Column("type", sa.String(10), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("selected_date", sa.Date(), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_periodicity")),
        if_not_exists=True,
    )

    # Conditionally add the `periodicity_id` column back to the `events` table
    # There's no way to do this in alembic because there's no native IF NOT EXISTS syntax for altering tables
    # So we use raw SQL
    op.execute("""
    DO
    $$
        BEGIN
            IF NOT EXISTS (SELECT 1
                           FROM information_schema.columns
                           WHERE table_name = 'events'
                             AND column_name = 'periodicity_id') 
            THEN
                ALTER TABLE events ADD COLUMN periodicity_id uuid DEFAULT gen_random_uuid() NOT NULL;
            END IF;
        END
    $$;
    """)

    # Conditionally repopulate the `periodicity` table
    # We do lose some data here (e.g. the original `id`, `created_at`, `updated_at`, `migrated_date`, `migrated_updated`),
    # because we can't recover that data from the `events` table
    op.execute("""
        INSERT INTO periodicity (id, is_deleted, type, start_date, end_date, selected_date)
        SELECT e.periodicity_id, e.is_deleted, e.periodicity, e.start_date, e.end_date, e.selected_date
        FROM events e
        WHERE NOT EXISTS (SELECT 1 FROM periodicity)
        """)


def downgrade() -> None:
    pass
