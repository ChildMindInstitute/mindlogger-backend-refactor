"""Remove nickname from guest account

Revision ID: 63a2a290c7e6
Revises: 69b1dfaf3c0d
Create Date: 2023-12-04 15:45:11.543448

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "63a2a290c7e6"
down_revision = "69b1dfaf3c0d"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    result = conn.execute(
        sa.text(
            f"""
                UPDATE user_applet_accesses SET nickname=NULL 
                WHERE user_id in ( 
                                    SELECT id 
                                    FROM users 
                                    WHERE is_anonymous_respondent=TRUE
                                );
            """
        )
    )


def downgrade() -> None:
    pass
