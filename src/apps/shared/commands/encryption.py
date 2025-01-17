import collections
from typing import Optional

import typer
from rich import print
from rich.style import Style
from rich.table import Table
from sqlalchemy import Unicode
from sqlalchemy.dialects.postgresql import dialect
from sqlalchemy_utils import StringEncryptedType

from apps.shared.encryption import get_key
from config import settings
from infrastructure.commands.utils import coro
from infrastructure.database import atomic, session_manager
from infrastructure.database.base import Base

app = typer.Typer()


ARBITRARY_TABLES_LIST = ("answers", "answers_items")


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
    for app in settings.migrations_apps:
        __import__(f"apps.{app}.db.schemas")

    mapping = collections.defaultdict(list)
    for mapper in Base.registry.mappers:
        table_name = mapper.class_.__tablename__
        for column in mapper.columns:
            if isinstance(column.type, StringEncryptedType):
                if table_name in ARBITRARY_TABLES_LIST:
                    raise ValueError(
                        f"Table {table_name} should not contain StringEncryptedType. "
                        "This table can be in arbitrary database and this database does not have pgcrypto extenstion"
                    )
                else:
                    mapping[table_name].append(column.name)
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
        help="Hex of secret key to decrypt data, if not key specified, default settings key will be used.",
    ),
    encrypt_secret_key: Optional[str] = typer.Option(
        None,
        "--encrypt-secret-key",
        "-e",
        help="Hex of secret key to encrypt data, if not key specified, default settings key will be used.",
    ),
    tables: Optional[list[str]] = typer.Argument(
        None,
        help="Tables which data need to reencrypt, "
        "if no table names are provided data in ALL allowed tables "
        "will be reencrypted.",
    ),
) -> None:
    session_maker = session_manager.get_session()
    decrypt_key = decrypt_secret_key if decrypt_secret_key else settings.secrets.secret_key
    encrypt_key = encrypt_secret_key if encrypt_secret_key else settings.secrets.secret_key
    decrypt_key = f"decode('{decrypt_key}', 'hex')"
    encrypt_key = f"decode('{encrypt_key}', 'hex')"
    table_name_column_name_map = await get_table_name_column_name_map()
    tables = tables if tables else list(table_name_column_name_map.keys())
    print_data_table(table_name_column_name_map)
    typer.confirm("Are you sure that you want to reencrypt columns in tables avobe?", abort=True)
    async with session_maker() as session:
        async with atomic(session):
            for table_name in tables:
                print(f"Started reencrypting data in the table {table_name}")
                columns = table_name_column_name_map.get(table_name, [])
                if not columns:
                    print(f"[red][bold]{table_name}[/bold] table does not have encrypted columns. Skipped[red]")
                    continue
                for column in columns:
                    print(f"Update column {column}")
                    sql = f"""
                        update {table_name}
                        set {column} = encrypt_internal(decrypt_internal({column}, {decrypt_key}), {encrypt_key})
                        where {column} is not null
                    """
                    await session.execute(sql)
                print(f"Finished reencrypting data in the table {table_name}")
    print("Reencryption is ended")
