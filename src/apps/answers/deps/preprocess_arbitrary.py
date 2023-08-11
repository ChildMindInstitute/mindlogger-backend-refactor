import uuid

from fastapi import Body, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from apps.answers.domain import AppletAnswerCreate
from apps.workspaces.service.workspace import WorkspaceService
from infrastructure.database import atomic
from infrastructure.database.core import get_specific_session
from infrastructure.database.deps import get_session

__all__ = [
    "get_arbitrary_session",
    "preprocess_arbitrary_by_applet_id",
    "preprocess_arbitrary_by_applet_schema",
]


async def get_arbitrary_info(
        applet_id: uuid.UUID, session: AsyncSession
) -> str | None:
    if applet_id:
        service = WorkspaceService(session, uuid.uuid4())
        server_info = await service.get_arbitrary_info(applet_id)
        if server_info and server_info.use_arbitrary:
            return server_info.database_uri
    return None


async def preprocess_arbitrary_by_applet_schema(
    schema: AppletAnswerCreate = Body(...), session=Depends(get_session)
):
    db_uri = await get_arbitrary_info(schema.applet_id, session)
    if db_uri:
        session_ = await anext(get_specific_session(db_uri))
        async with atomic(session_):
            yield session_
    else:
        yield None


async def preprocess_arbitrary_by_applet_id(
    applet_id: uuid.UUID, session=Depends(get_session)
):
    db_uri = await get_arbitrary_info(applet_id, session)
    if db_uri:
        session_ = await anext(get_specific_session(db_uri))
        async with atomic(session_):
            yield session_
    else:
        yield None
