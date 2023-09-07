"""Change fields type

Revision ID: 6268b3e094a3
Revises: a4b4299c90c5
Create Date: 2023-09-05 11:59:57.741477

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "6268b3e094a3"
down_revision = "a4b4299c90c5"
branch_labels = None
depends_on = None


def upgrade() -> None:

    # Change type to Text
    op.alter_column('users', 'first_name', type_=sa.Text())
    op.alter_column('users', 'last_name', type_=sa.Text())
    op.alter_column('users_workspaces', 'workspace_name', type_=sa.Text())
    op.alter_column('invitations', 'first_name', type_=sa.Text())
    op.alter_column('invitations', 'last_name', type_=sa.Text())
    op.alter_column('alerts', 'alert_message', type_=sa.Text())


def downgrade() -> None:

    # Revert to previous type
    op.alter_column('users', 'first_name', type_=sa.String(length=50))
    op.alter_column('users', 'last_name', type_=sa.String(length=50))
    op.alter_column('users_workspaces', 'workspace_name', type_=sa.String(length=100))
    op.alter_column('invitations', 'first_name', type_=sa.String(length=50))
    op.alter_column('invitations', 'last_name', type_=sa.String(length=50))
    op.alter_column('alerts', 'alert_message', type_=sa.String())
