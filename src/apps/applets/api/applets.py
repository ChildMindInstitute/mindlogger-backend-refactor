import uuid
from copy import deepcopy

from fastapi import Body, Depends

from apps.applets.domain import (
    AppletFolder,
    AppletName,
    AppletUniqueName,
    PublicAppletHistoryChange,
    PublicHistory,
)
from apps.applets.domain.applet import (
    AppletDataRetention,
    AppletDetailPublic,
    AppletInfoPublic,
)
from apps.applets.domain.applet_create import AppletCreate
from apps.applets.domain.applet_link import AppletLink, CreateAccessLink
from apps.applets.domain.applet_update import AppletUpdate
from apps.applets.domain.applets import public_detail, public_history_detail
from apps.applets.filters import AppletQueryParams, AppletUsersQueryParams
from apps.applets.service import AppletHistoryService, AppletService
from apps.applets.service.applet_history import (
    retrieve_applet_by_version,
    retrieve_versions,
)
from apps.authentication.deps import get_current_user
from apps.shared.domain.response import Response, ResponseMulti
from apps.shared.query_params import QueryParams, parse_query_params
from apps.users.domain import User

__all__ = [
    "applet_create",
    "applet_update",
    "applet_retrieve",
    "applet_versions_retrieve",
    "applet_version_retrieve",
    "applet_version_changes_retrieve",
    "applet_list",
    "applet_delete",
    "applet_set_folder",
    "applet_unique_name_get",
    "applet_link_create",
    "applet_link_get",
    "applet_link_delete",
    "applet_set_data_retention",
    "applet_users_list",
]

from apps.workspaces.domain.user_applet_access import PublicAppletUser
from apps.workspaces.service.user_applet_access import UserAppletAccessService
from infrastructure.database import atomic, session_manager
from infrastructure.http import get_language


async def applet_list(
    user: User = Depends(get_current_user),
    language: str = Depends(get_language),
    query_params: QueryParams = Depends(parse_query_params(AppletQueryParams)),
    session=Depends(session_manager.get_session),
) -> ResponseMulti[AppletInfoPublic]:
    async with atomic(session):
        applets = await AppletService(
            session, user.id
        ).get_list_by_single_language(language, deepcopy(query_params))
        count = await AppletService(
            session, user.id
        ).get_list_by_single_language_count(deepcopy(query_params))
    return ResponseMulti(
        result=[AppletInfoPublic.from_orm(applet) for applet in applets],
        count=count,
    )


async def applet_retrieve(
    id_: uuid.UUID,
    user: User = Depends(get_current_user),
    language: str = Depends(get_language),
    session=Depends(session_manager.get_session),
) -> Response[AppletDetailPublic]:
    async with atomic(session):
        applet = await AppletService(
            session, user.id
        ).get_single_language_by_id(id_, language)
    return Response(result=AppletDetailPublic.from_orm(applet))


async def applet_users_list(
    id_: uuid.UUID,
    user: User = Depends(get_current_user),
    query_params: QueryParams = Depends(
        parse_query_params(AppletUsersQueryParams)
    ),
    session=Depends(session_manager.get_session),
) -> ResponseMulti[PublicAppletUser]:
    async with atomic(session):
        users = await UserAppletAccessService(
            session, user.id, id_
        ).get_applet_users(deepcopy(query_params))
        count = await UserAppletAccessService(
            session, user.id, id_
        ).get_applet_users_count(deepcopy(query_params))
    return ResponseMulti(
        count=count, result=[PublicAppletUser.from_orm(user) for user in users]
    )


async def applet_create(
    user: User = Depends(get_current_user),
    schema: AppletCreate = Body(...),
    session=Depends(session_manager.get_session),
) -> Response[public_detail.Applet]:
    async with atomic(session):
        applet = await AppletService(session, user.id).create(schema)
    return Response(result=public_detail.Applet(**applet.dict()))


async def applet_update(
    id_: uuid.UUID,
    user: User = Depends(get_current_user),
    schema: AppletUpdate = Body(...),
    session=Depends(session_manager.get_session),
) -> Response[public_detail.Applet]:
    async with atomic(session):
        applet = await AppletService(session, user.id).update(id_, schema)
    return Response(result=public_detail.Applet(**applet.dict()))


async def applet_versions_retrieve(
    id_: uuid.UUID,
    user: User = Depends(get_current_user),
    session=Depends(session_manager.get_session),
) -> ResponseMulti[PublicHistory]:
    async with atomic(session):
        histories = await retrieve_versions(session, id_)
    return ResponseMulti(result=[PublicHistory(**h.dict()) for h in histories])


async def applet_version_retrieve(
    id_: uuid.UUID,
    version: str,
    user: User = Depends(get_current_user),
    session=Depends(session_manager.get_session),
) -> Response[public_history_detail.AppletDetailHistory]:
    async with atomic(session):
        applet = await retrieve_applet_by_version(session, id_, version)
        if not applet:
            return Response(result=None)
    return Response(
        result=public_history_detail.AppletDetailHistory(**applet.dict())
    )


async def applet_version_changes_retrieve(
    id_: uuid.UUID,
    version: str,
    user: User = Depends(get_current_user),
    session=Depends(session_manager.get_session),
) -> Response[PublicAppletHistoryChange]:
    async with atomic(session):
        changes = await AppletHistoryService(
            session, id_, version
        ).get_changes()
    return Response(result=PublicAppletHistoryChange(**changes.dict()))


async def applet_delete(
    id_: uuid.UUID,
    user: User = Depends(get_current_user),
    session=Depends(session_manager.get_session),
):
    async with atomic(session):
        await AppletService(session, user.id).delete_applet_by_id(id_)


async def applet_set_folder(
    applet_folder: AppletFolder,
    user: User = Depends(get_current_user),
    session=Depends(session_manager.get_session),
):
    async with atomic(session):
        await AppletService(session, user.id).set_applet_folder(applet_folder)


async def applet_unique_name_get(
    schema: AppletName = Body(...),
    user: User = Depends(get_current_user),
    session=Depends(session_manager.get_session),
) -> Response[AppletUniqueName]:
    async with atomic(session):
        new_name = await AppletService(session, user.id).get_unique_name(
            schema
        )
    return Response(result=AppletUniqueName(name=new_name))


async def applet_link_create(
    id_: uuid.UUID,
    user: User = Depends(get_current_user),
    schema: CreateAccessLink = Body(...),
    session=Depends(session_manager.get_session),
) -> Response[AppletLink]:
    async with atomic(session):
        access_link = await AppletService(session, user.id).create_access_link(
            applet_id=id_, create_request=schema
        )
    return Response(result=access_link)


async def applet_link_get(
    id_: uuid.UUID,
    user: User = Depends(get_current_user),
    session=Depends(session_manager.get_session),
) -> Response[AppletLink]:
    async with atomic(session):
        access_link = await AppletService(session, user.id).get_access_link(
            applet_id=id_
        )
    return Response(result=access_link)


async def applet_link_delete(
    id_: uuid.UUID,
    user: User = Depends(get_current_user),
    session=Depends(session_manager.get_session),
):
    async with atomic(session):
        await AppletService(session, user.id).delete_access_link(applet_id=id_)


async def applet_set_data_retention(
    id_: uuid.UUID,
    schema: AppletDataRetention,
    user: User = Depends(get_current_user),
    session=Depends(session_manager.get_session),
):
    async with atomic(session):
        await AppletService(session, user.id).set_data_retention(
            applet_id=id_, data_retention=schema
        )
