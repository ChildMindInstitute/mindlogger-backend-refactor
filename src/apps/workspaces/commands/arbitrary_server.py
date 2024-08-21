import asyncio
import http
import io
import uuid
from typing import Optional

import httpx
import typer
from pydantic import ValidationError
from rich import print
from rich.style import Style
from rich.table import Table
from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.ext.asyncio import create_async_engine

from apps.answers.service import AnswerTransferService
from apps.file.storage import create_client, select_storage
from apps.users.cruds.user import UsersCRUD
from apps.users.errors import UserIsDeletedError, UserNotFound
from apps.workspaces.constants import StorageType
from apps.workspaces.domain.workspace import (
    WorkspaceArbitrary,
    WorkSpaceArbitraryConsoleOutput,
    WorkspaceArbitraryCreate,
    WorkspaceArbitraryFields,
)
from apps.workspaces.errors import ArbitraryServerSettingsError, WorkspaceNotFoundError
from apps.workspaces.service.workspace import WorkspaceService
from config import settings
from infrastructure.commands.utils import coro
from infrastructure.database import atomic, session_manager

app = typer.Typer()


async def get_version(database_url) -> str | None:
    engine = create_async_engine(database_url)
    async with engine.connect() as conn:
        try:
            db_result = await conn.execute(text("select version_num from alembic_version"))
        except ProgrammingError:
            return None
        result: str | None = db_result.scalar_one()
        return result


def print_data_table(data: WorkspaceArbitraryFields) -> None:
    table = Table(
        show_header=False,
        title="Arbitrary server settings",
        title_style=Style(bold=True),
    )
    for k, v in data.dict(by_alias=False).items():
        table.add_row(f"[bold]{k}[/bold]", str(v))

    print(table)


def error_msg(msg: str):
    print(f"[bold red]Error: {msg}[/bold red]")


def error(msg: str):
    error_msg(msg)
    raise typer.Abort()


@app.command(short_help="Add arbitrary server settings")
@coro
async def add(
    owner_email: str = typer.Argument(..., help="Workspace owner email"),
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
        error(loc_str + err["msg"])
    session_maker = session_manager.get_session()
    async with session_maker() as session:
        async with atomic(session):
            try:
                owner = await UsersCRUD(session).get_by_email(owner_email)
                await WorkspaceService(session, owner.id).set_arbitrary_server(data, rewrite=force)
            except WorkspaceNotFoundError as e:
                error(str(e))
            except ArbitraryServerSettingsError as e:
                print_data_table(e.data)
                error("Arbitrary server is already set. Use --force to rewrite.")
            except (UserNotFound, UserIsDeletedError):
                error(f"User with email {owner_email} not found")
    alembic_version = await get_version(data.database_uri)
    output = WorkSpaceArbitraryConsoleOutput(
        email=owner_email, user_id=owner.id, **data.dict(), alembic_version=alembic_version
    )
    print(
        "[green]Success: Run [bold]ping[/bold] command to check access. "
        "Don't forget to apply migrations for database.[/green]"
    )
    print_data_table(output)


@app.command(short_help="Show arbitrary server settings")
@coro
async def show(
    owner_email: Optional[str] = typer.Argument(None, help="Workspace owner email"),
):
    session_maker = session_manager.get_session()
    async with session_maker() as session:
        if owner_email:
            try:
                owner = await UsersCRUD(session).get_by_email(owner_email)
            except (UserNotFound, UserIsDeletedError):
                error(f"User with email {owner_email} not found")
            else:
                data = await WorkspaceService(session, owner.id).get_arbitrary_info_by_owner_id_if_use_arbitrary(
                    owner.id
                )
                if not data:
                    print(f"[bold green]Arbitrary settings are not configured for {owner_email}[/bold green]")
                    return
                arbitrary_fields = WorkspaceArbitraryFields.from_orm(data)
                try:
                    alembic_version = await get_version(data.database_uri)
                except asyncio.TimeoutError:
                    alembic_version = "[bold red]ERROR: Timeout[/bold red]"
                except Exception as e:
                    alembic_version = f"[bold red]ERROR: {e}[/bold red]"

                output = WorkSpaceArbitraryConsoleOutput(
                    **arbitrary_fields.dict(), email=owner_email, user_id=owner.id, alembic_version=alembic_version
                )
                print_data_table(output)
        else:
            workspaces = await WorkspaceService(session, uuid.uuid4()).get_arbitrary_list()
            user_crud = UsersCRUD(session)
            for data in workspaces:
                user = await user_crud.get_by_id(data.user_id)
                arbitrary_fields = WorkspaceArbitraryFields.from_orm(data)
                try:
                    alembic_version = await get_version(data.database_uri)
                except asyncio.TimeoutError:
                    alembic_version = "[bold red]ERROR: Timeout[/bold red]"
                except Exception as e:
                    alembic_version = f"[bold red]ERROR: {e}[/bold red]"
                output = WorkSpaceArbitraryConsoleOutput(
                    **arbitrary_fields.dict(),
                    email=user.email_encrypted,
                    user_id=user.id,
                    alembic_version=alembic_version,
                )
                print_data_table(output)


@app.command(short_help="Remove server settings for an workspace by email")
@coro
async def remove(
    owner_email: str = typer.Argument(..., help="Workspace owner email"),
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
                owner = await UsersCRUD(session).get_by_email(owner_email)
                await WorkspaceService(session, owner.id).set_arbitrary_server(data, rewrite=True)
            except (UserNotFound, UserIsDeletedError):
                error(f"User with email {owner_email} not found")
            except WorkspaceNotFoundError as e:
                error(str(e))
            else:
                print(f"[green]Abitrary settings for owner {owner_email} with id {owner.id} are removed![/green]")


@app.command(
    short_help=(
        "Ping arbitrary database and check uploading to the provided bucket to be sure that everything work correct"
    )
)
@coro
async def ping(owner_email: str = typer.Argument(..., help="Workspace owner email")) -> None:
    session_maker = session_manager.get_session()
    async with session_maker() as session:
        try:
            owner = await UsersCRUD(session).get_by_email(owner_email)
            data = await WorkspaceService(session, owner.id).get_arbitrary_info_by_owner_id_if_use_arbitrary(
                owner.id, in_use_only=False
            )
        except (UserNotFound, UserIsDeletedError):
            error(f"User with email {owner_email} not found")
        except WorkspaceNotFoundError as e:
            error(str(e))
        if data is None:
            print(f"[green]Arbitrary settings are not configured for user {owner_email}.[/green]")
            return
        async with session_manager.get_session(data.database_uri)() as arb_session:
            try:
                print("Check database availability.")
                await arb_session.execute("select current_date")
                print(f"[green]Database for user [bold]{owner_email}[/bold] is available.[/green]")
            except asyncio.TimeoutError:
                error_msg("Timeout error")
            except Exception as e:
                error_msg(str(e))
        print(f'Check bucket "{data.storage_bucket}" availability.')
        storage = await select_storage(owner_id=owner.id, session=session)
        key = "mindlogger.txt"
        presigned_data = storage.generate_presigned_post(data.storage_bucket, key)
        print(f"Presigned POST fields are following: {presigned_data['fields'].keys()}")
        file = io.BytesIO(b"")
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    presigned_data["url"], data=presigned_data["fields"], files={"file": (key, file)}
                )
                if response.status_code == http.HTTPStatus.NO_CONTENT:
                    print(f"[green]Bucket {data.storage_bucket} for user {owner_email} is available.[/green]")
                else:
                    error_msg("File upload error")
                    print(response.content)
            except httpx.HTTPError as e:
                error_msg("File upload error")
                error(str(e))


def _s_lower(s: str | None) -> str | None:
    return s.lower() if s else s


def _is_db_same(source_arb_data: WorkspaceArbitrary | None, target_arb_data: WorkspaceArbitrary | None) -> bool:
    checks = [source_arb_data is None, target_arb_data is None]
    if all(checks):
        return True
    if any(checks):
        return False
    assert source_arb_data
    assert target_arb_data
    return _s_lower(source_arb_data.database_uri) == _s_lower(target_arb_data.database_uri)


def _is_bucket_same(source_arb_data: WorkspaceArbitrary | None, target_arb_data: WorkspaceArbitrary | None) -> bool:
    checks = [source_arb_data is None, target_arb_data is None]
    if all(checks):
        return True
    if any(checks):
        return False

    to_check = (
        "storage_type",
        "storage_url",
        "storage_access_key",
        "storage_secret_key",
        "storage_region",
        "storage_bucket",
    )

    for attr in to_check:
        if _s_lower(getattr(source_arb_data, attr)) != _s_lower(getattr(target_arb_data, attr)):
            return False

    return True


@app.command(
    short_help=(
        "Copy answers (DB records, files) from source arbitrary (or internal) to target arbitrary (or internal) server."
        "WARNING: ensure source and target are different!"
    )
)
@coro
async def copy_applet_answers(
    applet_ids: list[uuid.UUID] = typer.Argument(..., help="A list of Applet IDs for data copying."),
    source_owner_email: Optional[str] = typer.Option(
        None,
        "--src-owner-email",
        "-s",
        help="Source workspace owner email. Internal server will be used by default.",
    ),
    target_owner_email: Optional[str] = typer.Option(
        None,
        "--tgt-owner-email",
        "-t",
        help="Target workspace owner email. Internal server will be used by default.",
    ),
    skip_db: bool = typer.Option(
        False,
        is_flag=True,
        help="Skip DB records copying.",
    ),
    skip_files: bool = typer.Option(
        False,
        is_flag=True,
        help="Skip files copying.",
    ),
) -> None:
    if not source_owner_email and not target_owner_email:
        error("Source or target should be set")
    if skip_db and skip_files:
        error("Nothing to copy: DB and files skipped")

    source_arb_data = None
    target_arb_data = None

    session_maker = session_manager.get_session()
    async with session_maker() as session:
        user_crud = UsersCRUD(session)

        if source_owner_email:
            try:
                source_owner = await user_crud.get_by_email(source_owner_email)
                source_arb_data = await WorkspaceService(
                    session, source_owner.id
                ).get_arbitrary_info_by_owner_id_if_use_arbitrary(source_owner.id, in_use_only=False)
            except (UserNotFound, UserIsDeletedError):
                error(f"User with email {source_owner_email} not found")
            except WorkspaceNotFoundError as e:
                error(str(e))
        if target_owner_email:
            try:
                target_owner = await user_crud.get_by_email(target_owner_email)
                target_arb_data = await WorkspaceService(
                    session, target_owner.id
                ).get_arbitrary_info_by_owner_id_if_use_arbitrary(target_owner.id, in_use_only=False)
            except (UserNotFound, UserIsDeletedError):
                error(f"User with email {target_owner} not found")
            except WorkspaceNotFoundError as e:
                error(str(e))

        if source_arb_data is None and target_arb_data is None:
            error("No arbitrary data found")

        copy_db = False if skip_db else not _is_db_same(source_arb_data, target_arb_data)
        copy_files = False if skip_files else not _is_bucket_same(source_arb_data, target_arb_data)

        source_db_uri = source_arb_data.database_uri if source_arb_data else settings.database.url
        target_db_uri = target_arb_data.database_uri if target_arb_data else settings.database.url
        async with session_manager.get_session(source_db_uri)() as source_session:
            await AnswerTransferService.check_db(source_session)
            async with session_manager.get_session(target_db_uri)() as target_session:
                await AnswerTransferService.check_db(target_session)

                source_bucket = create_client(source_arb_data)
                try:
                    await source_bucket.check()
                except Exception as e:
                    error_msg(str(e))
                    raise
                target_bucket = create_client(target_arb_data)
                try:
                    await target_bucket.check()
                except Exception as e:
                    error_msg(str(e))
                    raise

                service = AnswerTransferService(session, source_session, target_session, source_bucket, target_bucket)

                for applet_id in applet_ids:
                    await service.transfer(applet_id, copy_db=copy_db, copy_files=copy_files)
