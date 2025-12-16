"""add_recovery_codes_table_and_generated_at_field

Revision ID: 476c854a8417
Revises: e6d01d46f10e
Create Date: 2025-11-24 19:29:53.652251

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "476c854a8417"
down_revision = "e6d01d46f10e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create recovery_codes table
    op.create_table(
        "recovery_codes",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("migrated_date", sa.DateTime(), nullable=True),
        sa.Column("migrated_updated", sa.DateTime(), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code_hash", sa.Text(), nullable=False),
        sa.Column("code_encrypted", sa.Text(), nullable=False),
        sa.Column("used", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("used_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_recovery_codes_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_recovery_codes")),
    )

    # Create index on user_id for fast lookups
    op.create_index(
        op.f("ix_recovery_codes_user_id"),
        "recovery_codes",
        ["user_id"],
        unique=False,
    )

    # Add recovery_codes_generated_at column to users table
    op.add_column(
        "users",
        sa.Column("recovery_codes_generated_at", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    # Remove recovery_codes_generated_at column from users table
    op.drop_column("users", "recovery_codes_generated_at")

    # Drop index
    op.drop_index(op.f("ix_recovery_codes_user_id"), table_name="recovery_codes")

    # Drop recovery_codes table
    op.drop_table("recovery_codes")

