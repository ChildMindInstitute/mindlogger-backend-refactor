"""UserId emails to UserId uuid

Revision ID: 5130eba9f698
Revises: 87d3c8a8de55
Create Date: 2023-12-21 17:25:42.256018

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "5130eba9f698"
down_revision = "b993457637ad"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text(
            """
        with
        uuid_email as (
            select distinct
                email,
                id::text
            from users
        )
        update notification_logs
        set user_id = ue.id
        from uuid_email ue
        where ue.email = encode(sha224(user_id::bytea), 'hex');
    """
        )
    )
    # Delete non-existing emails
    conn.execute(
        sa.text("""delete from notification_logs where user_id like '%@%'""")
    )


def downgrade() -> None:
    pass
