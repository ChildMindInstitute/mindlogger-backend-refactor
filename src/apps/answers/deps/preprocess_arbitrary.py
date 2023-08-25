import uuid
from typing import Optional

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from apps.answers.domain import ArbitraryPreprocessor
from apps.workspaces.service.workspace import WorkspaceService
from config import settings
from infrastructure.database.core import session_manager
from infrastructure.database.deps import get_session

__all__ = [
    "get_arbitrary_info",
    "preprocess_arbitrary_url",
    "get_answer_session",
]


async def get_arbitrary_info(
    applet_id: uuid.UUID | None, session: AsyncSession
) -> str | None:
    if applet_id:
        service = WorkspaceService(session, uuid.uuid4())
        server_info = await service.get_arbitrary_info(applet_id)
        if server_info and server_info.use_arbitrary:
            return server_info.database_uri
    return None


async def preprocess_arbitrary_url(
    applet_id: uuid.UUID | None = None,
    schema: ArbitraryPreprocessor | None = None,
    session=Depends(get_session),
) -> Optional[str]:
    if schema:
        return await get_arbitrary_info(schema.applet_id, session)
    elif applet_id:
        return await get_arbitrary_info(applet_id, session)
    else:
        return None


async def get_answer_session(url=Depends(preprocess_arbitrary_url)):
    if url:
        session_maker = session_manager.get_session(url)
    else:
        session_maker = session_manager.get_session()

    if settings.env == "testing":
        yield session_maker
    else:
        async with session_maker() as session:
            yield session
