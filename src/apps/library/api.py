import uuid
from copy import deepcopy

from fastapi import Body, Depends

from apps.authentication.deps import get_current_user
from apps.library.domain import (
    AppletLibraryCreate,
    AppletLibraryFull,
    AppletLibraryInfo,
    AppletLibraryUpdate,
    Cart,
    CartQueryParams,
    LibraryNameCheck,
    LibraryQueryParams,
    PublicLibraryItem,
)
from apps.library.service import LibraryService
from apps.shared.domain import Response, ResponseMulti
from apps.shared.query_params import QueryParams, parse_query_params
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
    query_params: QueryParams = Depends(
        parse_query_params(LibraryQueryParams)
    ),
    session=Depends(get_session),
) -> ResponseMulti[PublicLibraryItem]:
    async with atomic(session):
        applets = await LibraryService(session).get_all_applets(
            deepcopy(query_params)
        )
        count = await LibraryService(session).get_applets_count(
            deepcopy(query_params)
        )

    return ResponseMulti(
        result=applets,
        count=count,
    )


async def library_get_by_id(
    library_id: uuid.UUID,
    session=Depends(get_session),
) -> Response[PublicLibraryItem]:
    async with atomic(session):
        applet = await LibraryService(session).get_applet_by_id(library_id)

    return Response(result=PublicLibraryItem(**applet.dict()))


async def library_get_url(
    applet_id: uuid.UUID,
    session=Depends(get_session),
    user=Depends(get_current_user),
) -> Response[AppletLibraryInfo]:
    async with atomic(session):
        await CheckAccessService(session, user.id).check_link_edit_access(
            applet_id
        )
        info = await LibraryService(session).get_applet_url(applet_id)

    return Response(result=info)


async def library_update(
    library_id: uuid.UUID,
    schema: AppletLibraryUpdate = Body(...),
    session=Depends(get_session),
    user=Depends(get_current_user),
) -> Response[AppletLibraryFull]:
    async with atomic(session):
        library_item: AppletLibraryFull = await LibraryService(
            session
        ).update_shared_applet(library_id, schema, user.id)
    return Response(result=library_item)


async def cart_get(
    user: User = Depends(get_current_user),
    session=Depends(get_session),
    query_params: QueryParams = Depends(parse_query_params(CartQueryParams)),
) -> ResponseMulti[PublicLibraryItem]:
    async with atomic(session):
        service = LibraryService(session)
        cart = await service.get_cart(user.id)
        items = await service.filter_cart_items(cart, query_params)
        count = len(cart.cart_items) if cart and cart.cart_items else 0
    return ResponseMulti(result=items, count=count)


async def cart_add(
    user: User = Depends(get_current_user),
    schema: Cart = Body(...),
    session=Depends(get_session),
) -> Response[Cart]:
    async with atomic(session):
        cart = await LibraryService(session).add_to_cart(user.id, schema)
    return Response(result=cart)
