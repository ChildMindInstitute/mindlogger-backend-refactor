"""hash user email

Revision ID: 879e5b56ca8b
Revises: 956eafa172cb
Create Date: 2023-08-21 19:00:48.767562

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = "879e5b56ca8b"
down_revision = "956eafa172cb"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        update users set email=concat(email, '_duplication') where email not like '%@%' and email in (select encode(sha224(email::bytea), 'hex') as email from users where email like '%@%');  
        update users set email=encode(sha224(email::bytea), 'hex') where email like '%@%';
    """)


def downgrade() -> None:
    return
