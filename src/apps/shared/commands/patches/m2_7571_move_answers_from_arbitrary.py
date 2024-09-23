import uuid

from rich import print
from sqlalchemy.ext.asyncio import AsyncSession

from apps.answers.service import AnswerTransferService
from apps.file.storage import create_client
from apps.workspaces.errors import WorkspaceNotFoundError
from apps.workspaces.service.workspace import WorkspaceService
from infrastructure.database import session_manager

APPLET_IDS = (
    uuid.UUID("710f76b5-de7f-47ca-9442-62dd21b329bf"),
    uuid.UUID("88a6cc9e-9a1d-4809-a0cb-3dafbd98e709"),
)
ARBITRARY_WORKSPACE_OWNER_ID = uuid.UUID("607dd47c-c87a-395a-6ed5-658600000000")

INSERT_BATCH_SIZE = 1000


def error_msg(msg: str):
    print(f"[bold red]Error: {msg}[/bold red]")


async def main(
    session: AsyncSession,
    arbitrary_session: AsyncSession = None,
    *args,
    **kwargs,
):
    owner_id = ARBITRARY_WORKSPACE_OWNER_ID
    try:
        arb_info = await WorkspaceService(session, owner_id).get_arbitrary_info_by_owner_id_if_use_arbitrary(
            owner_id, in_use_only=False
        )
        if not arb_info or not arb_info.database_uri:
            error_msg("Arbitrary db not found")
            return
    except WorkspaceNotFoundError as e:
        error_msg(str(e))
        raise

    session_maker = session_manager.get_session(arb_info.database_uri)
    async with session_maker() as arb_session:
        arb_bucket = create_client(arb_info)
        try:
            await arb_bucket.check()
        except Exception as e:
            error_msg(str(e))
            raise

        internal_bucket = create_client(None)
        try:
            await internal_bucket.check()
        except Exception as e:
            error_msg(str(e))
            raise

        service = AnswerTransferService(session, arb_session, session, arb_bucket, internal_bucket)
        await service.check_db(arb_session)

        for applet_id in APPLET_IDS:
            await service.transfer(applet_id)
