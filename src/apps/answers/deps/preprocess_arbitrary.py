import uuid
from typing import Optional

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from apps.answers.domain import ArbitraryPreprocessor
from apps.subjects.services import SubjectsService
from apps.workspaces.service.workspace import WorkspaceService
from infrastructure.database.core import session_manager
from infrastructure.database.deps import get_session

__all__ = [
    "get_arbitrary_info",
    "preprocess_arbitrary_url",
    "get_answer_session",
    "get_answer_session_by_subject"
]


async def get_arbitrary_info(applet_id: uuid.UUID | None, session: AsyncSession) -> str | None:
    if applet_id:
        service = WorkspaceService(session, uuid.uuid4())
        server_info = await service.get_arbitrary_info(applet_id)
        if server_info and server_info.use_arbitrary:
            return server_info.database_uri
    return None


async def get_arbitraries_map(applet_ids: list[uuid.UUID], session: AsyncSession) -> dict[str | None, list[uuid.UUID]]:
    """Returning map {"arbitrary_uri": [applet_ids]}"""
    return await WorkspaceService(session, uuid.uuid4()).get_arbitraries_map(applet_ids)


async def preprocess_arbitrary_url(
    applet_id: uuid.UUID | None = None,
    schema: ArbitraryPreprocessor | None = None,
    session=Depends(get_session),
) -> Optional[str]:
    if schema and schema.applet_id:
        return await get_arbitrary_info(schema.applet_id, session)
    elif applet_id:
        return await get_arbitrary_info(applet_id, session)
    else:
        return None


async def get_answer_session(url=Depends(preprocess_arbitrary_url)):
    if not url:
        yield None
    else:
        session_maker = session_manager.get_session(url)
        async with session_maker() as session:
            yield session


async def get_answer_session_by_owner_id(
    owner_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    service = WorkspaceService(session, uuid.uuid4())
    server_info = await service.get_arbitrary_info_by_owner_id(owner_id)
    if server_info and server_info.use_arbitrary:
        url = server_info.database_uri
        if not url:
            yield None
        else:
            session_maker = session_manager.get_session(url)
            async with session_maker() as session:
                yield session
    else:
        yield None


async def get_answer_session_by_subject(
    subject_id: uuid.UUID,
    session: AsyncSession = Depends(get_session)
):
    subject = await SubjectsService(session, uuid.uuid4()).get(subject_id)
    if not subject:
        yield None
    service = WorkspaceService(session, uuid.uuid4())
    assert subject
    server_info = await service.get_arbitrary_info(subject.applet_id)
    if server_info and server_info.use_arbitrary:
        url = server_info.database_uri
        if not url:
            yield None
        else:
            session_maker = session_manager.get_session(url)
            async with session_maker() as session:
                yield session
    else:
        yield None
