import uuid
from typing import Annotated

import typer
from rich import print

from apps.subjects.crud import SubjectsCrud
from apps.users import UserIsDeletedError, UserNotFound, UsersCRUD
from apps.users.domain import SoftDeleteUserRequest
from infrastructure.commands.utils import coro
from infrastructure.database import atomic, session_manager

app = typer.Typer(short_help="Manage users")

NAME_CHECK = "NAME_REMOVED_BY_CURIOUS_TEAM"


@app.command(short_help="Soft delete a user", help="Replace a user's email and other PII fields with junk data")
@coro
async def soft_delete(
    user_id: Annotated[uuid.UUID, typer.Argument(help="User Id")],
    applet_id: Annotated[uuid.UUID, typer.Argument(help="Applet Id")],
    ticket_id: Annotated[str, typer.Argument(help="Ticket Id")],
    yes: Annotated[bool, typer.Option(help="Do not prompt for confirmation")] = False,
):
    s_maker = session_manager.get_session()
    async with s_maker() as session:
        async with atomic(session):
            users_crud = UsersCRUD(session)
            subjects_crud = SubjectsCrud(session)

            try:
                user = await users_crud.get_by_id(user_id)
            except UserNotFound:
                raise typer.BadParameter("User does not exist")
            except UserIsDeletedError:
                raise typer.BadParameter("User is already deleted")

            if not user:
                raise typer.BadParameter("User does not exist")

            if NAME_CHECK in user.first_name:
                raise typer.BadParameter("User is already soft deleted")

            print(f"[bold green]Found user {user_id}[/bold green]")

            subject = await subjects_crud.get(user_id, applet_id)
            if not subject:
                raise typer.BadParameter("Subject does not exist for applet")

            if subject.is_deleted:
                raise typer.BadParameter("Subject is already deleted")
            if NAME_CHECK in subject.first_name:
                raise typer.BadParameter("Subject is already soft deleted")

            print(f"[bold green]Found subject {subject.id}[/bold green]")

            if not yes:
                typer.confirm("Are you sure that you soft delete this user?", abort=True)

            name = f"{NAME_CHECK}-{ticket_id}"
            email = f"{uuid.uuid4()}@{NAME_CHECK}.com"

            update_schema = SoftDeleteUserRequest(first_name=name, last_name=name, email=email)

            subject.first_name = name
            subject.last_name = name
            subject.nickname = name
            subject.email = email

            async with atomic(session):
                await users_crud.update(user, update_schema)
                await subjects_crud.update(subject)

            print(f"[bold green]User {user_id} soft deleted successfully[/bold green]")


# Placeholder until there are more commands, mostly for testing
# https://typer.tiangolo.com/tutorial/commands/one-or-multiple/#one-command-and-one-callback
@app.callback()
def callback():
    pass
