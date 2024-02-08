"""Create function to decrypt on database level

Revision ID: 736adb0ea547
Revises: 54123357967a
Create Date: 2024-02-07 18:59:13.999978

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "736adb0ea547"
down_revision = "54123357967a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(sa.DDL(
        """
        create or replace function decrypt_internal(text, bytea) returns text
        language plpgsql as
        $$
        declare
            res text;
            key_digest bytea;
        BEGIN
            key_digest = digest($2, 'sha256');
            select
                convert_from(
                    rtrim(
                        decrypt_iv(
                            decode($1, 'base64'),
                            key_digest,
                            substring(key_digest, 1, 16),
                            'aes-cbc/pad:none'
                        ),
                        '*'::bytea
                    ),
                    'UTF8'
                )
            into res;
        
            return res;
        end;
        $$;        
        """
    ))


def downgrade() -> None:
    op.execute(sa.DDL("DROP FUNCTION decrypt_internal(text, bytea)"))

