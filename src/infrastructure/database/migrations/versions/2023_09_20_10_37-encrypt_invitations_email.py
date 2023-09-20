"""encrypt invitations email

Revision ID: af9a602d25ad
Revises: 67dc7cd54c43
Create Date: 2023-09-20 10:37:24.620957

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy import String, Unicode
from sqlalchemy_utils.types.encrypted.encrypted_type import StringEncryptedType

from apps.shared.encryption import decrypt, encrypt, get_key

# revision identifiers, used by Alembic.
revision = "af9a602d25ad"
down_revision = "67dc7cd54c43"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    result = conn.execute(
        sa.text("SELECT id, email FROM invitations WHERE email IS NOT NULL")
    )
    op.alter_column(
        "invitations",
        "email",
        type_=StringEncryptedType(Unicode, get_key),
        default=None
    )
    for row in result:
        pk, email = row
        encrypted_field = (
            StringEncryptedType(Unicode, get_key)
            .process_bind_param(email, dialect=conn.dialect)
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


def downgrade() -> None:
    conn = op.get_bind()
    result = conn.execute(
        sa.text("SELECT id, email FROM invitations WHERE email IS NOT NULL")
    )
    op.alter_column("invitations", "email", type_=sa.Text(), default=None)

    for row in result:
        pk, email = row
        decrypted_field = (
            StringEncryptedType(Unicode, get_key)
            .process_result_value(email, dialect=conn.dialect)
        )
        conn.execute(
            sa.text(
                f"""
                    UPDATE invitations 
                    SET email = :decrypted_field 
                    WHERE id = :pk
                """
            ),
            {"decrypted_field": decrypted_field, "pk": pk}
        )

