import asyncio
import importlib
import uuid
from pathlib import Path
from typing import Optional

import typer
from rich import print
from rich.style import Style
from rich.table import Table

from apps.shared.commands.domain import Patch
from apps.shared.commands.patch import PatchRegister
from apps.workspaces.errors import WorkspaceNotFoundError
from apps.workspaces.service.workspace import WorkspaceService
from infrastructure.commands.utils import coro
from infrastructure.database import atomic, session_manager

PatchRegister.register(
    file_path="slider_tickmark_label.py",
    task_id="M2-3781",
    description="Slider tick marks and labels fix patch",
    manage_session=False,
)
PatchRegister.register(
    file_path="m2_4906_populate_user_id_in_invitations.sql",
    task_id="M2-4906",
    description="Populate user_id column in declined/approved invitations",
    manage_session=False,
)
PatchRegister.register(
    file_path="m2_5045_auto_advance.py",
    task_id="M2-5045",
    description="Set auto_advance=True to all existing singleSelect items without auto_advance flag",  # noqa : E501
    manage_session=False,
)
PatchRegister.register(
    file_path="m2_4951_add_missing_job_status_to_the_job_status_enum.sql",
    task_id="M2-4951",
    description="Add missing job_status to the job_status enum",
    manage_session=False,
)
PatchRegister.register(
    file_path="m2_6057_drawing_proportion.py",
    task_id="M2-6057",
    description="Set proportion.enabled=True to Maki's applets",
    manage_session=False,
)
PatchRegister.register(
    file_path="m2_6968_create_flows_old_versions.py",
    task_id="M2-6968",
    description="Create flow history records for particular applets",
    manage_session=False,
)
PatchRegister.register(
    file_path="m2_6879_create_deleted_respondents.py",
    task_id="M2-6879",
    description="[Subject] Create deleted respondents roles",
    manage_session=False,
)
PatchRegister.register(
    file_path="m2_5551_delete_invitations_of_existing_respondent.sql",
    task_id="M2-5551",
    description="[Subject] Delete pending invitations of existing respondent",
)
PatchRegister.register(
    file_path="m2_4608_create_subjects.sql",
    task_id="M2-4608",
    description="[Subject] Create subject record for each respondent",
)
PatchRegister.register(
    file_path="m2_4611_add_answer_subjects.py",
    task_id="M2-4611",
    description="[Subject] Add subject ids for answers in internal and arbitrary DBs",
)
PatchRegister.register(
    file_path="m2_4613_create_invitation_subjects.py",
    task_id="M2-4613",
    description="[Subject] Create subjects for pending invitations",
)
PatchRegister.register(
    file_path="m2_5018_migrate_reviewer_respondents_list.py",
    task_id="M2-5018",
    description="[Subject] Replace reviewer respondent list with subject list",
)
PatchRegister.register(
    file_path="m2_5116_add_alert_subjects.sql",
    task_id="M2-5116",
    description="[Subject] Populate alerts with subject ids",
)
PatchRegister.register(
    file_path="m2_6757_replace_amp_sanitizer.py",
    task_id="M2-6757",
    description="Change ampersand sanitizer to symbol '&'",
)
PatchRegister.register(
    file_path="m2_6504_update_subject_tags.sql",
    task_id="M2-6504",
    description="[MultiinformantR1] Update tag fields for managers/reviewers subjects",
)
PatchRegister.register(
    file_path="m2_6733_add_answer_input_subjects.py",
    task_id="M2-6733",
    description="[MultiinformantR1] Add input subject ids for answers in internal and arbitrary DBs",
)
PatchRegister.register(
    file_path="m2_7203_migrate_secret_ids.py",
    task_id="M2-7203",
    description="[Migration] Migrate missed secret ids",
)

PatchRegister.register(
    file_path="m2_7366_set_auto_assign_to_true_for_activities_and_flows.py",
    task_id="M2-7366",
    description="Set auto_assign to true for existing activities and flows",
    manage_session=False,
)

app = typer.Typer()


def print_data_table(data: list[Patch]):
    table = Table(
        "Task ID",
        "Description",
        "Manage session inside patch",
        show_header=True,
        title="Patches",
        title_style=Style(bold=True),
    )

    for patch in data:
        table.add_row(
            f"[bold]{patch.task_id}[bold]",
            str(patch.description),
            str(patch.manage_session),
        )
    print(table)


def wrap_error_msg(msg):
    return f"[bold red]Error: \n{msg}[/bold red]"


@app.command("list", short_help="Show list of registered patches.")
@coro
async def show():
    data = PatchRegister.get_all()
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
    patch = PatchRegister.get_by_task_id(task_id)
    if not patch:
        print(wrap_error_msg("Patch not registered"))
    else:
        await exec_patch(patch, owner_id)

    return


async def exec_patch(patch: Patch, owner_id: Optional[uuid.UUID]):
    session_maker = session_manager.get_session()
    arbitrary = None
    async with session_maker() as session:
        async with atomic(session):
            if owner_id:
                try:
                    arbitrary = await WorkspaceService(
                        session, owner_id
                    ).get_arbitrary_info_by_owner_id_if_use_arbitrary(owner_id)
                    if not arbitrary:
                        raise WorkspaceNotFoundError("Workspace not found")

                except WorkspaceNotFoundError as e:
                    print(wrap_error_msg(e))
                    raise

    arbitrary_session_maker = None
    if arbitrary:
        arbitrary_session_maker = session_manager.get_session(arbitrary.database_uri)

    session_maker = session_manager.get_session()

    print(
        f"[bold green]Execute patch {patch.task_id} ({patch.file_path})[/bold green]"  # noqa: E501
    )
    if patch.file_path.endswith(".sql"):
        # execute sql file
        async with session_maker() as session:
            async with atomic(session):
                try:
                    with open(
                        (str(Path(__file__).parent.resolve()) + "/patches/" + patch.file_path),
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
                str(__package__) + ".patches." + patch.file_path.replace(".py", ""),
            )

            # if manage_session is True, pass sessions to patch_file main
            if patch.manage_session:
                await patch_file.main(session_maker, arbitrary_session_maker)
            else:
                async with session_maker() as session:
                    async with atomic(session):
                        if arbitrary_session_maker:
                            async with arbitrary_session_maker() as arbitrary_session:  # noqa: E501
                                async with atomic(arbitrary_session):
                                    await patch_file.main(session, arbitrary_session)
                        else:
                            await patch_file.main(session)

            print(
                f"[bold green]Patch {patch.task_id} executed[/bold green]"  # noqa: E501
            )
        except Exception as e:
            msg = str(e)
            if isinstance(e, asyncio.TimeoutError):
                msg = "Timeout Error"
            print(wrap_error_msg(msg))
