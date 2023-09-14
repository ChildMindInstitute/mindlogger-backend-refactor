"""Implement encod decod with db models

Revision ID: 67dc7cd54c43
Revises: 41458766b541
Create Date: 2023-09-14 10:24:58.093851

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy import Unicode
from sqlalchemy.dialects import postgresql
from sqlalchemy_utils.types.encrypted.encrypted_type import StringEncryptedType

from apps.shared.encryption import decrypt, encrypt, get_key

# revision identifiers, used by Alembic.
revision = "67dc7cd54c43"
down_revision = "41458766b541"
branch_labels = None
depends_on = None

migrate_fields = [
    ("users", "email_encrypted"),
    ("users", "first_name"),
    ("users", "last_name"),
    ("users_workspaces", "workspace_name"),
    ("invitations", "first_name"),
    ("invitations", "last_name"),
    ("answer_notes", "note"),
    ("alerts", "alert_message")
]


def upgrade() -> None:
    conn = op.get_bind()
    # Drop unused column
    op.drop_column("users", "email_aes_encrypted")

    for table_name, column_name in migrate_fields:
        # Selection field with old decryption
        result = conn.execute(
            sa.text(f"SELECT id, {column_name} FROM {table_name} WHERE {column_name} IS NOT NULL")
        )

        # Changing the field type for encryption with db models
        op.alter_column(table_name, column_name, type_=StringEncryptedType(Unicode, get_key), default=None)

        # Encrypt with db models
        for row in result:
            table_id, field_encrypted = row
            field = decrypt(bytes.fromhex(field_encrypted)).decode("utf-8")
            encrypted_field = StringEncryptedType(Unicode, get_key).process_bind_param(
                field, dialect=conn.dialect
            )
            conn.execute(
                sa.text(f"UPDATE {table_name} SET {column_name} = :encrypted_field WHERE id = :table_id"),
                {"encrypted_field": encrypted_field, "table_id": table_id}
            )


def downgrade() -> None:
    conn = op.get_bind()
    # Column restoration
    op.add_column(
        "users",
        sa.Column(
            "email_aes_encrypted",
            postgresql.BYTEA(),
            autoincrement=False,
            nullable=True,
        ),
    )

    for table_name, column_name in migrate_fields:
        # Selection field with db models decryption
        result = conn.execute(
            sa.text(f"SELECT id, {column_name} FROM {table_name} WHERE {column_name} IS NOT NULL")
        )

        # Changing the field type for old encryption
        op.alter_column(table_name, column_name, type_=sa.Text())

        # Encrypt with old encryption
        for row in result:
            table_id, encrypted_field = row
            decrypted_field = StringEncryptedType(Unicode, get_key).process_result_value(
                encrypted_field, dialect=conn.dialect
            )
            field_encrypted = encrypt(bytes(decrypted_field, "utf-8")).hex()
            conn.execute(
                sa.text(f"UPDATE {table_name} SET {column_name} = :field_encrypted WHERE id = :table_id"),
                {"field_encrypted": field_encrypted, "table_id": table_id}
            )
