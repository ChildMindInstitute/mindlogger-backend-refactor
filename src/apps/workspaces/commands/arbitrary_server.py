import uuid
from typing import Optional

import typer
from pydantic import ValidationError
from rich import print
from rich.style import Style
from rich.table import Table
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from apps.workspaces.constants import StorageType
from apps.workspaces.domain.workspace import (
    WorkSpaceArbitraryConsoleOutput,
    WorkspaceArbitraryCreate,
    WorkspaceArbitraryFields,
)
from apps.workspaces.errors import ArbitraryServerSettingsError, WorkspaceNotFoundError
from apps.workspaces.service.workspace import WorkspaceService
from infrastructure.commands.utils import coro
from infrastructure.database import atomic, session_manager

app = typer.Typer()


async def get_version(database_url):
    engine = create_async_engine(database_url)
    async with engine.connect() as conn:
        db_result = await conn.execute(text("select version_num from alembic_version"))
        return db_result.scalar_one()


def print_data_table(data: WorkspaceArbitraryFields):
    table = Table(
        show_header=False,
        title="Arbitrary server settings",
        title_style=Style(bold=True),
    )
    for k, v in data.dict(by_alias=False).items():
        table.add_row(f"[bold]{k}[/bold]", str(v))

    print(table)


def wrap_error_msg(msg):
    return f"[bold red]Error: \n{msg}[/bold red]"


@app.command(short_help="Add arbitrary server settings")
@coro
async def add(
    owner_id: uuid.UUID = typer.Argument(..., help="Workspace owner id"),
    database_uri: str = typer.Option(
        ...,
        "--db-uri",
        "-d",
        help="Arbitrary server database uri",
    ),
    storage_type: StorageType = typer.Option(
        ...,
        "--storage-type",
        "-t",
        help="Arbitrary server storage type",
    ),
    storage_url: str = typer.Option(
        None,
        "--storage-url",
        "-u",
        help="Arbitrary server storage url",
    ),
    storage_access_key: str = typer.Option(
        None,
        "--storage-access-key",
        "-a",
        help="Arbitrary server storage access key",
    ),
    storage_secret_key: str = typer.Option(
        ...,
        "--storage-secret-key",
        "-s",
        help="Arbitrary server storage secret key",
    ),
    storage_region: str = typer.Option(
        None,
        "--storage-region",
        "-r",
        help="Arbitrary server storage region",
    ),
    storage_bucket: str = typer.Option(
        None,
        "--storage-bucket",
        "-b",
        help="Arbitrary server storage bucket",
    ),
    use_arbitrary: bool = typer.Option(
        True,
        is_flag=True,
        help="Use arbitrary server for workspace",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        is_flag=True,
        help="Rewrite existing settings",
    ),
):
    try:
        data = WorkspaceArbitraryCreate(
            database_uri=database_uri,
            storage_type=storage_type,
            storage_url=storage_url,
            storage_access_key=storage_access_key,
            storage_secret_key=storage_secret_key,
            storage_region=storage_region,
            storage_bucket=storage_bucket,
            use_arbitrary=use_arbitrary,
        )
    except ValidationError as e:
        err = next(iter(e.errors()))
        loc = err["loc"]
        loc_str = ""
        if isinstance(loc[-1], int) and len(loc) > 1:
            loc_str = f"{loc[-2]}.{loc[-1]}: "
        elif loc[-1] != "__root__":
            loc_str = f"{loc[-1]}: "
        print(wrap_error_msg(loc_str + err["msg"]))
        return

    session_maker = session_manager.get_session()
    async with session_maker() as session:
        async with atomic(session):
            try:
                await WorkspaceService(session, owner_id).set_arbitrary_server(data, rewrite=force)
            except WorkspaceNotFoundError as e:
                print(wrap_error_msg(e))
            except ArbitraryServerSettingsError as e:
                print(wrap_error_msg("Arbitrary server is already set. " "Use --force to rewrite."))
                print_data_table(e.data)
            else:
                print("[bold green]Success:[/bold green]")
                output = WorkSpaceArbitraryConsoleOutput(user_id=owner_id, **data.dict())
                print_data_table(output)


@app.command(short_help="Show arbitrary server settings")
@coro
async def show(
    owner_id: Optional[uuid.UUID] = typer.Argument(None, help="Workspace owner id"),
):
    session_maker = session_manager.get_session()
    async with session_maker() as session:
        if owner_id:
            data = await WorkspaceService(session, owner_id).get_arbitrary_info_by_owner_id_if_use_arbitrary(owner_id)
            if not data:
                print("[bold green]" "Arbitrary server not configured" "[/bold green]")
                return
            alembic_version = await get_version(data.database_uri)
            arbitrary_fields = WorkspaceArbitraryFields.from_orm(data)
            output = WorkSpaceArbitraryConsoleOutput(
                **arbitrary_fields.dict(), user_id=owner_id, alembic_version=alembic_version
            )
            print_data_table(output)
        else:
            workspaces = await WorkspaceService(session, uuid.uuid4()).get_arbitrary_list()
            for data in workspaces:
                alembic_version = await get_version(data.database_uri)
                arbitrary_fields = WorkspaceArbitraryFields.from_orm(data)
                output = WorkSpaceArbitraryConsoleOutput(
                    **arbitrary_fields.dict(), user_id=data.user_id, alembic_version=alembic_version
                )
                print_data_table(output)


@app.command(short_help="Remove arbitrary server settings")
@coro
async def remove(
    owner_id: uuid.UUID = typer.Argument(..., help="Workspace owner id"),
):
    data = WorkspaceArbitraryFields(
        database_uri=None,
        storage_type=None,
        storage_url=None,
        storage_access_key=None,
        storage_secret_key=None,
        storage_region=None,
        storage_bucket=None,
        use_arbitrary=False,
    )

    session_maker = session_manager.get_session()
    async with session_maker() as session:
        async with atomic(session):
            try:
                await WorkspaceService(session, owner_id).set_arbitrary_server(data, rewrite=True)
            except WorkspaceNotFoundError as e:
                print(wrap_error_msg(e))
            else:
                print(f"[bold green]Abitrary setting for owner {owner_id} are removed![/bold green]")
