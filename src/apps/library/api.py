from fastapi import Body, Depends

from apps.authentication.deps import get_current_user
from apps.library.domain import (
    AppletLibraryCreate,
    AppletLibraryFull,
    LibraryNameCheck,
)
from apps.library.service import LibraryService
from apps.shared.domain import Response
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
            session, user.id
        ).share_applet(schema)
    return Response(result=library_item)


async def library_check_name(
    user: User = Depends(get_current_user),
    schema: LibraryNameCheck = Body(...),
    session=Depends(get_session),
):
    async with atomic(session):
        await LibraryService(session, user.id).check_applet_name(schema.name)
