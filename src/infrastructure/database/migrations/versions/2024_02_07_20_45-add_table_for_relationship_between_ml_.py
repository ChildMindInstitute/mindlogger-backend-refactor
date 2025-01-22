"""Add table for relationship between ML and LORIS users

Revision ID: 9e5cad6da163
Revises: efc3d92c9e05
Create Date: 2024-02-07 20:45:56.046453

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "9e5cad6da163"
down_revision = "efc3d92c9e05"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'ml_loris_user_relationship',
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("timezone('utc', now())"),
            nullable=True,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("timezone('utc', now())"),
            nullable=True,
        ),
        sa.Column("migrated_date", sa.DateTime(), nullable=True),
        sa.Column("migrated_updated", sa.DateTime(), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=True),
        sa.Column('ml_user_uuid', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('loris_user_id', sa.String, unique=True, nullable=False)
    )


def downgrade() -> None:
    op.drop_table('ml_loris_user_relationship')
