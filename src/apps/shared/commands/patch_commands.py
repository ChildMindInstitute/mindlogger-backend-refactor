import asyncio
import importlib
import uuid
from functools import wraps
from pathlib import Path
from typing import Optional

import typer
from rich import print
from rich.style import Style
from rich.table import Table

from apps.shared.commands.domain import PatchRegister
from apps.shared.commands.patch import Patch
from apps.workspaces.errors import WorkspaceNotFoundError
from apps.workspaces.service.workspace import WorkspaceService
from infrastructure.database import atomic, session_manager

app = typer.Typer()


def coro(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        return asyncio.run(f(*args, **kwargs))

    return wrapper


def print_data_table(data: list[PatchRegister]):
    table = Table(
        "Task ID",
        "Description",
        "Order",
        show_header=True,
        title="Patches",
        title_style=Style(bold=True),
    )

    for patch in data:
        table.add_row(
            f"[bold]{patch.task_id}[bold]",
            str(patch.description),
            str(patch.order),
        )
    print(table)


def wrap_error_msg(msg):
    return f"[bold red]Error: \n{msg}[/bold red]"


@app.command(short_help="Show list of registered patches.")
@coro
async def show():
    data = Patch.get_all()
    if not data:
        print("[bold green]Patches not registered[/bold green]")
        return
    print_data_table(data)


@app.command(short_help="Execute registered patch.")
@coro
async def exec(
    task_id: str = typer.Argument(..., help="Patch task id"),
    owner_id: Optional[uuid.UUID] = typer.Option(
        None,
        "--owner-id",
        "-o",
        help="Workspace owner id",
    ),
):
    patches = Patch.get_all_by_task_id(task_id)
    if not patches:
        print(wrap_error_msg("Patches not registered"))
        return

    for patch in patches:
        await exec_patch(patch, owner_id)

    return


async def exec_patch(patch: PatchRegister, owner_id: Optional[uuid.UUID]):
    session_maker = session_manager.get_session()
    arbitrary = None
    try:
        async with session_maker() as session:
            async with atomic(session):
                if owner_id:
                    try:
                        arbitrary = await WorkspaceService(
                            session, owner_id
                        ).get_arbitrary_info_by_owner_id(owner_id)
                        if not arbitrary:
                            raise WorkspaceNotFoundError("Workspace not found")

                    except WorkspaceNotFoundError as e:
                        print(wrap_error_msg(e))
                        raise
    finally:
        await session_maker.remove()

    if arbitrary:
        session_maker = session_manager.get_session(arbitrary.database_uri)
    else:
        session_maker = session_manager.get_session()

    try:
        async with session_maker() as session:
            async with atomic(session):
                if patch.file_path.endswith(".sql"):
                    # execute sql file
                    try:
                        with open(
                            (
                                str(Path(__file__).parent.resolve())
                                + "/patches/"
                                + patch.file_path
                            ),
                            "r",
                        ) as f:
                            sql = f.read()
                            await session.execute(sql)
                            await session.commit()
                            print(
                                f"[bold green]Patch {patch.task_id} executed[/bold green]"  # noqa: E501
                            )
                            return
                    except Exception as e:
                        print(wrap_error_msg(e))

                elif patch.file_path.endswith(".py"):
                    try:
                        # run main from the file
                        patch_file = importlib.import_module(
                            str(__package__)
                            + ".patches."
                            + patch.file_path.replace(".py", ""),
                        )
                        await patch_file.main(session)
                        print(
                            f"[bold green]Patch {patch.task_id} executed[/bold green]"  # noqa: E501
                        )
                    except Exception as e:
                        print(wrap_error_msg(e))
    finally:
        await session_maker.remove()
