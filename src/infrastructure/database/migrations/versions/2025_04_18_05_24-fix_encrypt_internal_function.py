"""Fix encrypt_internal function

Revision ID: 2a9ee1cea9c6
Revises: c4e312ad0798
Create Date: 2025-04-18 05:24:08.432983

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "2a9ee1cea9c6"
down_revision = "c4e312ad0798"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(sa.DDL(
        """
        create or replace function encrypt_internal(text, bytea) returns text
        language plpgsql as
        $$
        declare
            res text;
            key_digest bytea;
            block_size integer;
            padded_value bytea;
        begin
            key_digest = digest($2, 'sha256');
            block_size = 16;
            padded_value = (concat($1, repeat('*', block_size - octet_length($1) %% block_size)))::bytea;
            select
                encode(
                    encrypt_iv(
                        padded_value,
                        key_digest,
                        substring(key_digest, 1, block_size),
                        'aes-cbc/pad:none'
                    ),
                    'base64'
                )
            into res;

            return res;
        end;
        $$;
        """
    ))


def downgrade() -> None:
    op.execute(sa.DDL(
        """
        create or replace function encrypt_internal(text, bytea) returns text
        language plpgsql as
        $$
        declare
            res text;
            key_digest bytea;
            block_size integer;
            padded_value bytea;
        begin
            key_digest = digest($2, 'sha256');
            block_size = 16;
            padded_value = (concat($1, repeat('*', block_size - length($1) %% block_size)))::bytea;
            select
                encode(
                    encrypt_iv(
                        padded_value,
                        key_digest,
                        substring(key_digest, 1, block_size),
                        'aes-cbc/pad:none'
                    ),
                    'base64'
                )
            into res;

            return res;
        end;
        $$;
        """
    ))
