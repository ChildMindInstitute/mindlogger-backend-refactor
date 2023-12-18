import typer
from sqlalchemy import Unicode
from sqlalchemy.dialects.postgresql import dialect

from typing import Optional

from rich import print
from rich.style import Style
from rich.table import Table
from sqlalchemy_utils import StringEncryptedType

from apps.shared.encryption import get_key
from infrastructure.database import atomic, session_manager
from infrastructure.commands.utils import coro

app = typer.Typer()


@app.command(short_help="Encrypt data (internal encryption in DB)")
@coro
async def encrypt(data: str):
    encrypted_val = StringEncryptedType(Unicode, get_key).process_bind_param(data, dialect=dialect.name)

    print(encrypted_val)


@app.command(short_help="Decrypt data (internal encryption in DB)")
@coro
async def decrypt(encrypted_data: str):
    decrypted = StringEncryptedType(Unicode, get_key).process_result_value(encrypted_data, dialect=dialect.name)

    print(decrypted)


# Hardcode is bad, but for now it is ok
TABLE_NAME_COLUMN_NAME_MAP = {
    "users": ["email_encrypted", "first_name", "last_name"],
    "user_applet_accesses": ["nickname"],
    "users_workspaces": [
        "workspace_name",
        "database_uri",
        "storage_type",
        "storage_access_key",
        "storage_secret_key",
        "storage_region",
        "storage_url",
        "storage_bucket",
    ],
    "transfer_ownership": ["email"],
    "alerts": ["alert_message"],
    "answer_notes": ["note"],
    "invitations": ["email", "first_name", "last_name", "nickname"],
}

ROWS_PER_SELECT_LIMIT = 1000


def print_data_table() -> None:
    table = Table(
        *("Table name", "List of encrypted columns"),
        title="Tables with encrypted columns",
        title_style=Style(bold=True),
    )
    for k, v in TABLE_NAME_COLUMN_NAME_MAP.items():
        table.add_row(f"[bold]{k}[/bold]", "\n".join(v), end_section=True)

    print(table)


@app.command(short_help="Show tables with columns which have ecnrypted data")
@coro
async def show() -> None:
    print_data_table()


@app.command(short_help="Reencrypt data")
@coro
async def reencrypt(
    decrypt_secret_key: Optional[str] = typer.Option(
        None,
        "--decrypt-secret-key",
        "-d",
        help="Hex of secret key to decrypt data, " "if not key specified, default settings key will be used.",
    ),
    encrypt_secret_key: Optional[str] = typer.Option(
        None,
        "--encrypt-secret-key",
        "-e",
        help="Hex of secret key to encrypt data, " "if not key specified, default settings key will be used.",
    ),
    tables: Optional[list[str]] = typer.Argument(
        None,
        help="Tables which data need to reencrypt, "
        "if no table names are provided data in ALL allowed tables "
        "will be reencrypted.",
    ),
) -> None:
    session_maker = session_manager.get_session()
    decrypt_key = bytes.fromhex(decrypt_secret_key) if decrypt_secret_key else get_key()
    decryptor = StringEncryptedType(Unicode, decrypt_key)
    encrypt_key = bytes.fromhex(encrypt_secret_key) if encrypt_secret_key else get_key()
    encryptor = StringEncryptedType(Unicode, encrypt_key)
    tables = tables if tables else list(TABLE_NAME_COLUMN_NAME_MAP.keys())
    async with session_maker() as session:
        async with atomic(session):
            for table_name in tables:
                columns = TABLE_NAME_COLUMN_NAME_MAP.get(table_name, [])
                if not columns:
                    print("[red]" f"[bold]{table_name}[/bold] table does not have " "encrypted columns. Skipped[red]")
                    continue
                select_cols = ", ".join(columns)
                cnds = " or ".join([f"{col} is not null" for col in columns])
                limit = ROWS_PER_SELECT_LIMIT
                page = 1
                reencrypted = 0
                while True:
                    offset = (page - 1) * limit
                    sql = f"""
                        select
                            id,
                            {select_cols}
                        from {table_name}
                        where {cnds}
                        order by created_at, id
                        limit {limit} offset {offset}
                        for update
                    """
                    result = await session.execute(sql)
                    rows = result.all()
                    if not rows:
                        break
                    for row in rows:
                        id_ = row.id
                        to_update = {}
                        for col in columns:
                            value = getattr(row, col)
                            if value:
                                decrypted_value = decryptor.process_result_value(value, session.bind.dialect)
                                encrypted_value = encryptor.process_bind_param(
                                    decrypted_value,
                                    session.bind.dialect,
                                )
                                to_update[col] = encrypted_value
                        if to_update:
                            cols = ", ".join([f"{col} = :{col}" for col in to_update.keys()])
                            to_update["id"] = id_
                            await session.execute(f"update {table_name} set {cols} where id = :id", to_update)
                            reencrypted += 1
                    print(f"Batch {page} of rows in the table {table_name} was processed.")
                    if len(rows) < limit:
                        break
                    # Get next rows
                    page += 1
                print("[green]" f"{reencrypted} rows in [bold]{table_name}[/bold] table were reencrypted." "[green]")
