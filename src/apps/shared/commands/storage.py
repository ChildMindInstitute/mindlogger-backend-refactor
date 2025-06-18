from typing import Annotated

import typer
from rich import print
from rich.style import Style
from rich.table import Table

from config import settings
from infrastructure.commands.utils import coro
from infrastructure.database import atomic, session_manager

app = typer.Typer()

TABLES = {
    "activities": [
        ("extra_fields", "jsonb"),
        ("scores_and_reports", "jsonb"),
        ("image", "text"),
        ("splash_screen", "text"),
    ],
    "activity_histories": [
        ("scores_and_reports", "jsonb"),
        ("splash_screen", "text"),
        ("image", "text"),
        ("extra_fields", "jsonb"),
    ],
    "activity_item_histories": [
        ("config", "jsonb"),
        ("response_values", "jsonb"),
        ("question", "jsonb"),
    ],
    "activity_items": [
        ("config", "jsonb"),
        ("response_values", "jsonb"),
        ("question", "jsonb"),
        ("response_values", "jsonb"),
    ],
    "applet_histories": [
        ("report_email_body", "text"),
        ("about", "jsonb"),
        ("image", "text"),
        ("extra_fields", "jsonb"),
        ("watermark", "text"),
    ],
    "applets": [
        ("report_email_body", "text"),
        ("about", "jsonb"),
        ("image", "text"),
        ("extra_fields", "jsonb"),
        ("watermark", "text"),
    ],
    "cart": [
        ("cart_items", "jsonb"),
    ],
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


async def _migrate_text_field(session, table_name: str, column: str, search: str, replace: str):
    sql = f"""
        update {table_name}
        set {column} = replace({column}, '{search}', '{replace}')
    """
    print(sql)
    async with atomic(session):
        result = await session.execute(sql)
        print(f"Matched {result.rowcount} rows")


async def _migrate_jsonb_field(session, table_name: str, column: str, search: str, replace: str):
    sql = f"""
        update {table_name}
        set {column} = replace({column}::TEXT, '{search}', '{replace}')::jsonb
    """
    print(sql)
    async with atomic(session):
        result = await session.execute(sql)
        print(f"Matched {result.rowcount} rows")


@app.command(short_help="Migrate storage URLs")
@coro
async def migrate(
    source: Annotated[
        str, typer.Argument(help="Source value to replace (eg: mindlogger-applet-contents.s3.amazonaws.com)")
    ],
    replacement: Annotated[
        str, typer.Argument(help="Replacement value (eg: media.gettingcurious.com/mindlogger-legacy/content)")
    ],
) -> None:
    print_tables()
    print(f"Database host: {settings.database.host}")

    typer.confirm("Are you sure that you want to alter the fields shown above?", abort=True)

    session_maker = session_manager.get_session()
    async with session_maker() as session:
        for table_name, fields in TABLES.items():
            print(f"Started altering the table {table_name}")
            for field in fields:
                (col, col_type) = field
                print(f"  Started altering the column {col} ({col_type})")
                if col_type == "text":
                    await _migrate_text_field(session, table_name, col, source, replacement)
                elif col_type == "jsonb":
                    await _migrate_jsonb_field(session, table_name, col, source, replacement)
                else:
                    print(f"Unknown column type: {col_type}")
            print(f"Finished altering the table {table_name}")
    print("Finished altering the tables")


@app.command(short_help="Show tables with storage URLs")
@coro
async def show_tables() -> None:
    print_tables()
