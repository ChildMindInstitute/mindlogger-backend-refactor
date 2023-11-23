"""Encrypt workspace arbitrary fields

Revision ID: 0242aa768e9d
Revises: 8c59c7363c67
Create Date: 2023-11-11 19:02:32.433001

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy import Unicode
from sqlalchemy_utils import StringEncryptedType

from apps.shared.encryption import get_key

# revision identifiers, used by Alembic.
revision = "0242aa768e9d"
down_revision = "8c59c7363c67"
branch_labels = None
depends_on = None


to_encrypt = [
    "database_uri",
    "storage_type",
    "storage_access_key",
    "storage_secret_key",
    "storage_region",
    "storage_url",
    "storage_bucket",
]
table_name = "users_workspaces"


def upgrade() -> None:
    conn = op.get_bind()

    _cnd = " or ".join([f"{col} is not null" for col in to_encrypt])
    _cols = ", ".join(to_encrypt)
    result = conn.execute(
        sa.text(f"SELECT id, {_cols} FROM {table_name} WHERE {_cnd}")
    ).all()

    for column_name in to_encrypt:
        # Changing the field type for encryption with db models
        op.alter_column(
            table_name,
            column_name,
            type_=StringEncryptedType(Unicode, get_key),
            existing_type=sa.String(),
        )

    # Encrypt with db models
    for row in result:
        w_id = row.id
        data = {}
        for col in to_encrypt:
            if val := getattr(row, col):
                encrypted_val = StringEncryptedType(
                    Unicode, get_key
                ).process_bind_param(val, dialect=conn.dialect)
                data[col] = encrypted_val
        if data:
            upd_cols = ", ".join([f"{col} = :{col}" for col in data.keys()])
            data["id"] = w_id
            conn.execute(
                sa.text(f"UPDATE {table_name} SET {upd_cols} WHERE id = :id"),
                data,
            )


def downgrade() -> None:
    conn = op.get_bind()

    _cnd = " or ".join([f"{col} is not null" for col in to_encrypt])
    _cols = ", ".join(to_encrypt)
    result = conn.execute(
        sa.text(f"SELECT id, {_cols} FROM {table_name} WHERE {_cnd}")
    ).all()

    for column_name in to_encrypt:
        # Changing the field type for encryption with db models
        op.alter_column(
            table_name,
            column_name,
            type_=sa.String(),
            existing_type=StringEncryptedType(Unicode, get_key),
        )

    # Encrypt with db models
    for row in result:
        w_id = row.id
        data = {}
        for col in to_encrypt:
            if encrypted_val := getattr(row, col):
                val = StringEncryptedType(
                    Unicode, get_key
                ).process_result_value(encrypted_val, dialect=conn.dialect)
                data[col] = val
        if data:
            upd_cols = ", ".join([f"{col} = :{col}" for col in data.keys()])
            data["id"] = w_id
            conn.execute(
                sa.text(f"UPDATE {table_name} SET {upd_cols} WHERE id = :id"),
                data,
            )
