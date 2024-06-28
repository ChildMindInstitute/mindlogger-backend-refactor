import uuid

from rich import print
from sqlalchemy.ext.asyncio import AsyncSession

from apps.workspaces.service.workspace import WorkspaceService
from infrastructure.database import session_manager


async def update_answers(session):
    query = """
    update answers
    set input_subject_id = source_subject_id::uuid
    """
    await session.execute(query)


async def main(
    session: AsyncSession,
    arbitrary_session: AsyncSession = None,
    *args,
    **kwargs,
):
    print("Processing backend DB")
    await update_answers(session)
    await session.commit()
    print("Processing backend DB finished")

    workspaces = await WorkspaceService(session, uuid.uuid4()).get_arbitrary_list()

    print(f"Found {len(workspaces)} workspaces with arbitrary servers")

    processed = set()
    for i, workspace in enumerate(workspaces):
        if arb_uri := workspace.database_uri:
            print(f"Processing workspace#{i + 1} {workspace.id}")
            if arb_uri in processed:
                print(f"Workspace#{i + 1} DB already processed, skip...")
                continue
            processed.add(arb_uri)
            session_maker = session_manager.get_session(arb_uri)
            async with session_maker() as arb_session:
                try:
                    await update_answers(arb_session)
                    await arb_session.commit()
                    print(f"Processing workspace#{i + 1} {workspace.id} " f"finished")
                except Exception:
                    await arb_session.rollback()
                    print(f"[bold red]Workspace#{i + 1} {workspace.id} " f"processing error[/bold red]")
                    raise
