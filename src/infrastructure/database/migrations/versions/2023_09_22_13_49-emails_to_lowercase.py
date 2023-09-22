"""emails to lowercase

Revision ID: 5c717b96fb99
Revises: a7004a194160
Create Date: 2023-09-22 13:49:58.486725

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy import Unicode
from sqlalchemy_utils import StringEncryptedType

from apps.shared.encryption import get_key
from apps.shared.hashing import hash_sha224

# revision identifiers, used by Alembic.
revision = "5c717b96fb99"
down_revision = "a7004a194160"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    result = conn.execute(
        sa.text("SELECT id, email FROM invitations WHERE email IS NOT NULL")
    )
    for row in result:
        pk, email = row
        decrypted_field = str(
            StringEncryptedType(Unicode, get_key)
            .process_result_value(email, dialect=conn.dialect)
        ).lower()
        encrypted_field = (
            StringEncryptedType(Unicode, get_key)
            .process_bind_param(decrypted_field, dialect=conn.dialect)
        )
        conn.execute(
            sa.text(
                f"""
                        UPDATE invitations 
                        SET email = :encrypted_field 
                        WHERE id = :pk
                    """
            ),
            {"encrypted_field": encrypted_field, "pk": pk}
        )

    result = conn.execute(
        sa.text("""
            SELECT id, email_encrypted 
            FROM users 
            WHERE 
                email IS NOT NULL
                AND email_encrypted IS NOT NULL
            """
        )
    )
    for row in result:
        pk, email = row
        decrypted_field = str(
            StringEncryptedType(Unicode, get_key)
            .process_result_value(email, dialect=conn.dialect)
        ).lower()
        encrypted_field = (
            StringEncryptedType(Unicode, get_key)
            .process_bind_param(decrypted_field, dialect=conn.dialect)
        )
        hash_value = hash_sha224(decrypted_field)
        conn.execute(
            sa.text(
                f"""
                    UPDATE users 
                    SET 
                        email_encrypted = :encrypted_field,
                        email = :hash_value
                    WHERE id = :pk
                """
            ),
            {
                "pk": pk,
                "encrypted_field": encrypted_field,
                "hash_value": hash_value
            }
        )


def downgrade() -> None:
    pass
