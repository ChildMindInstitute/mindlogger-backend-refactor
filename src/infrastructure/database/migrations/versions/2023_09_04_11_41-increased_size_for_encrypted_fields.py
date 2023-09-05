"""Encrypt fields

Revision ID: 6e52c8f842a1
Revises: a4b4299c90c5
Create Date: 2023-09-04 11:41:54.030756

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "6e52c8f842a1"
down_revision = "a4b4299c90c5"
branch_labels = None
depends_on = None


def upgrade() -> None:

    # Double field sizes because encrypted field values are twice as large as unencrypted ones
    op.alter_column('users', 'first_name', type_=sa.String(length=100))
    op.alter_column('users', 'last_name', type_=sa.String(length=100))
    op.alter_column('users_workspaces', 'workspace_name', type_=sa.String(length=200))
    op.alter_column('invitations', 'first_name', type_=sa.String(length=100))
    op.alter_column('invitations', 'last_name', type_=sa.String(length=100))


def downgrade() -> None:

    # Revert to previous field size
    op.alter_column('users', 'first_name', type_=sa.String(length=50))
    op.alter_column('users', 'last_name', type_=sa.String(length=50))
    op.alter_column('users_workspaces', 'workspace_name', type_=sa.String(length=100))
    op.alter_column('invitations', 'first_name', type_=sa.String(length=50))
    op.alter_column('invitations', 'last_name', type_=sa.String(length=50))
