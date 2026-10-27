"""create user_legal_acceptances table

Revision ID: ac36a0d2ad01
Revises: f475633a2836
Create Date: 2026-09-29 14:29:27.852351

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "ac36a0d2ad01"
down_revision = "f475633a2836"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_legal_acceptances",
        sa.Column("is_deleted", sa.Boolean(), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("timezone('utc', now())"), nullable=True),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("timezone('utc', now())"), nullable=True),
        sa.Column("migrated_date", sa.DateTime(), nullable=True),
        sa.Column("migrated_updated", sa.DateTime(), nullable=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("doc_type", sa.String(length=50), nullable=False),
        sa.Column("version", sa.String(length=50), nullable=False),
        sa.Column("accepted_at", sa.DateTime(), nullable=False),
        sa.Column("source", sa.String(length=50), nullable=False),
        sa.Column("client_source", sa.String(length=50), nullable=True),
        sa.Column("ip_address", sa.Text(), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_user_legal_acceptances_user_id_users"), ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_user_legal_acceptances")),
    )
    op.create_index(
        "ix_user_legal_acceptances_user_id_doc_type", "user_legal_acceptances", ["user_id", "doc_type"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_user_legal_acceptances_user_id_doc_type", table_name="user_legal_acceptances")
    op.drop_table("user_legal_acceptances")
