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
                raise typer.BadParameter("User is already soft deleted")

            if not user:
                raise typer.BadParameter("User does not exist")

            print(f"[bold green]Found user {user_id} ({user.email})[/bold green]")

            subject = await subjects_crud.get(user_id, applet_id)
            if not subject:
                raise typer.BadParameter("Subject does not exist for applet")

            print(f"[bold green]Found subject {subject.id} ({subject.email})[/bold green]")

            typer.confirm("Are you sure that you soft delete this user?", abort=True)

            update_schema = SoftDeleteUserRequest(
                first_name="NAME_REMOVED_BY_CURIOUS_TEAM",
                last_name="NAME_REMOVED_BY_CURIOUS_TEAM",
                email="asdf@asf.com"
            )
            #
            # await users_crud.update(user, update_schema)
            #
            # subject.first_name = "NAME_REMOVED_BY_CURIOUS_TEAM"
            # subject.last_name = "NAME_REMOVED_BY_CURIOUS_TEAM"
            # subject.email = "asdf@asdf.com"
            #
            # await subjects_crud.update(subject)


# Placeholder until there are more commands, mostly for testing
# https://typer.tiangolo.com/tutorial/commands/one-or-multiple/#one-command-and-one-callback
@app.callback()
def callback():
    pass
