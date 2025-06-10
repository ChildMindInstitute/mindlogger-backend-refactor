import collections
from typing import Optional, Annotated

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

TABLES = {
    "activities": [
        ("extra_fields", "jsonb"),
        ("scores_and_reports", "jsonb"),
        ("image", "text"),
        ("splash_screen", "text")
    ],
    "activity_histories": [
        ("scores_and_reports", "jsonb")
    ]
}

def print_tables():
    # mapping: dict[str, list[tuple]]
    table = Table(
        *("Table name", "List of columns with image URLs"),
        title="Tables with Image URLs",
        title_style=Style(bold=True),
    )
    for k, v in TABLES.items():
        cols = [" -- ".join(col) for col in v]
        table.add_row(f"[bold]{k}[/bold]", "\n".join(cols), end_section=True)

    print(table)

@app.command(short_help="Migrate storage URLs")
@coro
async def migrate(
        source: Annotated[str, typer.Argument(help="Source value to replace (eg: mindlogger-applet-contents.s3.amazonaws.com)")],
        replacement: Annotated[str, typer.Argument(help="Replacement value (eg: media.gettingcurious.com/mindlogger-legacy/content)")]
) -> None:
    print_tables()
    typer.confirm("Are you sure that you want to alter the fields shown above?", abort=True)
    print("doing it")
    pass

@app.command(short_help="Show tables with storage URLs")
@coro
async def show_tables() -> None:
    print_tables()