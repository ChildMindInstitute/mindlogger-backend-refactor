import uuid

import typer
from rich import print

from apps.applets.service import AppletService
from apps.transfer_ownership.service import TransferService
from apps.users import User
from apps.users.cruds.user import UsersCRUD
from apps.users.errors import UserIsDeletedError, UserNotFound
from apps.workspaces.service.check_access import CheckAccessService
from infrastructure.commands.utils import coro
from infrastructure.database import atomic, session_manager

app = typer.Typer()


def error_msg(msg: str):
    print(f"[bold red]Error: {msg}[/bold red]")


def error(msg: str):
    error_msg(msg)
    raise typer.Abort()


async def _validate_access(session, user: User, applet_ids: list[uuid.UUID]):
    for applet_id in applet_ids:
        try:
            await AppletService(session, user.id).exist_by_id(applet_id)
            await CheckAccessService(session, user.id).check_create_transfer_ownership_access(applet_id)
        except Exception as e:
            error_msg(f"Applet access error: {applet_id}")
            error(str(e))


@app.command(help="Transfer ownership")
@coro
async def transfer_ownership(
    applet_ids: list[uuid.UUID] = typer.Argument(..., help="A list of Applet IDs for data copying."),
    source_owner_email: str = typer.Option(
        ...,
        "--src-owner-email",
        "-s",
        help="Source owner email.",
    ),
    target_owner_email: str = typer.Option(
        ...,
        "--tgt-owner-email",
        "-t",
        help="Target owner email.",
    ),
) -> None:
    source_owner_email = source_owner_email.lower()
    target_owner_email = target_owner_email.lower()
    if source_owner_email == target_owner_email:
        error("Emails are the same.")

    session_maker = session_manager.get_session()
    async with session_maker() as session:
        user_repo = UsersCRUD(session)
        try:
            source_user = await user_repo.get_by_email(source_owner_email)
        except (UserNotFound, UserIsDeletedError):
            error(f"User with email {source_owner_email} not found")
        await _validate_access(session, source_user, applet_ids)

        try:
            target_user = await user_repo.get_by_email(target_owner_email)
        except (UserNotFound, UserIsDeletedError):
            error(f"User with email {target_owner_email} not found")

        service_from = TransferService(session, source_user)
        service_to = TransferService(session, target_user)
        async with atomic(session):
            for applet_id in applet_ids:
                print(f"Transfer ownership for applet {applet_id}")
                transfer = await service_from.save_transfer_request(applet_id, target_owner_email, target_user.id)
                await service_to.accept_transfer(applet_id, transfer.key)
                print(f"[green]Transfer ownership for applet {applet_id} finished[/green]")
