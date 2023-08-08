import uuid

from fastapi import Body, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from apps.answers.domain import AppletAnswerCreate
from apps.workspaces.service.workspace_arbitrary import (
    WorkspaceArbitraryService,
)
from infrastructure.database import atomic
from infrastructure.database.core import get_specific_session
from infrastructure.database.deps import get_session

__all__ = [
    "preprocess_arbitrary_by_applet_id",
    "preprocess_arbitrary_by_applet_schema",
]


async def __get_arbitrary_session_or_none(
    applet_id: uuid.UUID, session: AsyncSession
) -> AsyncSession | None:
    arbitrary_server = await WorkspaceArbitraryService(session).read_by_applet(
        applet_id
    )
    if arbitrary_server:
        spec_session = await anext(
            get_specific_session(arbitrary_server.database_uri)
        )
        async with atomic(spec_session):
            yield spec_session
            await spec_session.commit()
    else:
        yield None


async def preprocess_arbitrary_by_applet_schema(
    schema: AppletAnswerCreate = Body(...),
    session=Depends(get_session),
) -> AsyncSession | None:
    yield __get_arbitrary_session_or_none(schema.applet_id, session)


async def preprocess_arbitrary_by_applet_id(
    applet_id: uuid.UUID, session: AsyncSession
):
    yield __get_arbitrary_session_or_none(applet_id, session)
