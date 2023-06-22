import uuid

from fastapi import Body, Depends

from apps.authentication.deps import get_current_user
from apps.library.domain import (
    AppletLibraryCreate,
    AppletLibraryFull,
    LibraryNameCheck,
    PublicLibraryItem,
)
from apps.library.service import LibraryService
from apps.shared.domain import Response, ResponseMulti
from apps.users import User
from apps.workspaces.service.check_access import CheckAccessService
from infrastructure.database import atomic
from infrastructure.database.deps import get_session


async def library_share_applet(
    user: User = Depends(get_current_user),
    schema: AppletLibraryCreate = Body(...),
    session=Depends(get_session),
) -> Response[AppletLibraryFull]:
    async with atomic(session):
        await CheckAccessService(
            session, user.id
        ).check_applet_share_library_access(schema.applet_id)

        library_item: AppletLibraryFull = await LibraryService(
            session
        ).share_applet(schema)
    return Response(result=library_item)


async def library_check_name(
    user: User = Depends(get_current_user),
    schema: LibraryNameCheck = Body(...),
    session=Depends(get_session),
):
    async with atomic(session):
        await LibraryService(session).check_applet_name(schema.name)


async def library_get_all(
    session=Depends(get_session),
) -> ResponseMulti[PublicLibraryItem]:
    async with atomic(session):
        applets = await LibraryService(session).get_all_applets()

    return ResponseMulti(
        result=applets,
        count=len(applets),
    )


async def library_get_by_id(
    library_id: uuid.UUID,
    session=Depends(get_session),
) -> Response[PublicLibraryItem]:
    async with atomic(session):
        applet = await LibraryService(session).get_applet_by_id(library_id)

    return Response(result=PublicLibraryItem(**applet.dict()))
