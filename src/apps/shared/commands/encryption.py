import collections
from typing import Optional

import typer
from rich import print
from rich.style import Style
from rich.table import Table
from sqlalchemy import MetaData, Unicode
from sqlalchemy.dialects.postgresql import dialect
from sqlalchemy_utils import StringEncryptedType

from apps.shared.encryption import get_key
from apps.shared.enums import ColumnCommentType
from config import settings
from infrastructure.commands.utils import coro
from infrastructure.database import atomic, session_manager
from infrastructure.database.core import build_engine

app = typer.Typer()


@app.command(short_help="Encrypt data (internal encryption in DB)")
@coro
async def encrypt(data: str) -> None:
    encrypted_val = StringEncryptedType(Unicode, get_key).process_bind_param(data, dialect=dialect.name)

    print(encrypted_val)


@app.command(short_help="Decrypt data (internal encryption in DB)")
@coro
async def decrypt(encrypted_data: str) -> None:
    decrypted = StringEncryptedType(Unicode, get_key).process_result_value(encrypted_data, dialect=dialect.name)

    print(decrypted)


ROWS_PER_SELECT_LIMIT = 1000


def print_data_table(mapping: dict[str, list[str]]) -> None:
    table = Table(
        *("Table name", "List of encrypted columns"),
        title="Tables with encrypted columns",
        title_style=Style(bold=True),
    )
    for k, v in mapping.items():
        table.add_row(f"[bold]{k}[/bold]", "\n".join(v), end_section=True)

    print(table)


async def get_table_name_column_name_map() -> dict[str, list[str]]:
    meta = MetaData()
    engine = build_engine(settings.database.url)
    async with engine.connect() as conn:
        await conn.run_sync(lambda sync_conn: meta.reflect(sync_conn.engine))
    mapping = collections.defaultdict(list)
    for table_name, table in meta.tables.items():
        for col in table.columns:
            if getattr(col, "comment", "") == ColumnCommentType.ENCRYPTED:
                mapping[table_name].append(col.name)
    return mapping


@app.command(short_help="Show tables with columns which have ecnrypted data")
@coro
async def show() -> None:
    mapping = await get_table_name_column_name_map()
    print_data_table(mapping)


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
    table_name_column_name_map = await get_table_name_column_name_map()
    tables = tables if tables else list(table_name_column_name_map.keys())
    print_data_table(table_name_column_name_map)
    typer.confirm("Are you sure that you want to reencrypt columns in tables avobe?", abort=True)
    async with session_maker() as session:
        async with atomic(session):
            for table_name in tables:
                columns = table_name_column_name_map.get(table_name, [])
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
    print("Reencryption is ended")
