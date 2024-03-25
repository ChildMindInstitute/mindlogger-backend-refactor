import typer
from sqlalchemy import Unicode
from sqlalchemy.dialects.postgresql import dialect
from sqlalchemy_utils import StringEncryptedType

from apps.shared.encryption import get_key
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
