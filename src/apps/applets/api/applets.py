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
    AppletSingleLanguageDetailForPublic,
    AppletSingleLanguageDetailPublic,
    AppletSingleLanguageInfoPublic,
)
from apps.applets.domain.applet_create_update import (
    AppletCreate,
    AppletDuplicateRequest,
    AppletUpdate,
)
from apps.applets.domain.applet_link import AppletLink, CreateAccessLink
from apps.applets.domain.applets import public_detail, public_history_detail
from apps.applets.domain.base import Encryption
from apps.applets.filters import AppletQueryParams
from apps.applets.service import AppletHistoryService, AppletService
from apps.applets.service.applet_history import (
    retrieve_applet_by_version,
    retrieve_versions,
)
from apps.authentication.deps import get_current_user
from apps.mailing.domain import MessageSchema
from apps.mailing.services import MailingService
from apps.shared.domain.response import Response, ResponseMulti
from apps.shared.query_params import QueryParams, parse_query_params
from apps.users.domain import User
from apps.workspaces.service.check_access import CheckAccessService
from infrastructure.database import atomic, session_manager
from infrastructure.http import get_language

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
    "applet_duplicate",
    "applet_retrieve_by_key",
]


async def applet_list(
    user: User = Depends(get_current_user),
    language: str = Depends(get_language),
    query_params: QueryParams = Depends(parse_query_params(AppletQueryParams)),
    session=Depends(session_manager.get_session),
) -> ResponseMulti[AppletSingleLanguageInfoPublic]:
    async with atomic(session):
        applets = await AppletService(
            session, user.id
        ).get_list_by_single_language(language, deepcopy(query_params))
        count = await AppletService(
            session, user.id
        ).get_list_by_single_language_count(deepcopy(query_params))
    return ResponseMulti(
        result=[
            AppletSingleLanguageInfoPublic.from_orm(applet)
            for applet in applets
        ],
        count=count,
    )


async def applet_retrieve(
    applet_id: uuid.UUID,
    user: User = Depends(get_current_user),
    language: str = Depends(get_language),
    session=Depends(session_manager.get_session),
) -> Response[AppletSingleLanguageDetailPublic]:
    async with atomic(session):
        await CheckAccessService(session, user.id).check_applet_detail_access(
            applet_id
        )
        applet = await AppletService(
            session, user.id
        ).get_single_language_by_id(applet_id, language)
    return Response(result=AppletSingleLanguageDetailPublic.from_orm(applet))


async def applet_retrieve_by_key(
    key: uuid.UUID,
    language: str = Depends(get_language),
    session=Depends(session_manager.get_session),
) -> Response[AppletSingleLanguageDetailForPublic]:
    async with atomic(session):
        applet = await AppletService(
            session, uuid.UUID("00000000-0000-0000-0000-000000000000")
        ).get_single_language_by_key(key, language)
    return Response(
        result=AppletSingleLanguageDetailForPublic.from_orm(applet)
    )


async def applet_create(
    owner_id: uuid.UUID,
    user: User = Depends(get_current_user),
    schema: AppletCreate = Body(...),
    session=Depends(session_manager.get_session),
) -> Response[public_detail.Applet]:
    async with atomic(session):
        await CheckAccessService(session, user.id).check_applet_create_access(
            owner_id
        )

        mail_service = MailingService()
        try:
            applet = await AppletService(session, owner_id).create(
                schema, user.id
            )
        except Exception:
            await mail_service.send(
                MessageSchema(
                    recipients=[user.email],
                    subject="Applet upload failed!",
                    body=mail_service.get_template(
                        path="applet_create_success_en",
                        first_name=user.first_name,
                        applet_name=schema.display_name,
                    ),
                )
            )
            raise
        await mail_service.send(
            MessageSchema(
                recipients=[user.email],
                subject="Applet upload success!",
                body=mail_service.get_template(
                    path="applet_create_success_en",
                    first_name=user.first_name,
                    applet_name=applet.display_name,
                ),
            )
        )
    return Response(result=public_detail.Applet(**applet.dict()))


async def applet_update(
    applet_id: uuid.UUID,
    user: User = Depends(get_current_user),
    schema: AppletUpdate = Body(...),
    session=Depends(session_manager.get_session),
) -> Response[public_detail.Applet]:
    # mail_service = MailingService()
    async with atomic(session):
        await CheckAccessService(session, user.id).check_applet_edit_access(
            applet_id
        )
        applet = await AppletService(session, user.id).update(
            applet_id, schema
        )
        # await mail_service.send(
        #     MessageSchema(
        #         recipients=[user.email],
        #         subject="Applet edit success!",
        #         body=mail_service.get_template(
        #             path="applet_edit_success_en",
        #             first_name=user.first_name,
        #             applet_name=applet.display_name,
        #         ),
        #     )
        # )
    return Response(result=public_detail.Applet(**applet.dict()))


async def applet_encryption_update(
    applet_id: uuid.UUID,
    user: User = Depends(get_current_user),
    schema: Encryption = Body(...),
    session=Depends(session_manager.get_session),
) -> Response[public_detail.Encryption]:
    async with atomic(session):
        await CheckAccessService(session, user.id).check_applet_edit_access(
            applet_id
        )
        await AppletService(session, user.id).update_encryption(
            applet_id, schema
        )
    return Response(result=public_detail.Encryption.from_orm(schema))


async def applet_duplicate(
    applet_id: uuid.UUID,
    user: User = Depends(get_current_user),
    schema: AppletDuplicateRequest = Body(...),
    session=Depends(session_manager.get_session),
) -> Response[public_detail.Applet]:
    mail_service = MailingService()
    async with atomic(session):
        await CheckAccessService(
            session, user.id
        ).check_applet_duplicate_access(applet_id)
        service = AppletService(session, user.id)
        applet_for_duplicate = await service.get_by_id_for_duplicate(applet_id)

        applet = await service.duplicate(
            applet_for_duplicate, schema.display_name, schema.encryption
        )

        await mail_service.send(
            MessageSchema(
                recipients=[user.email],
                subject="Applet duplicate success!",
                body=mail_service.get_template(
                    path="applet_duplicate_success_en",
                    first_name=user.first_name,
                    applet_name=applet.display_name,
                ),
            )
        )
    return Response(result=public_detail.Applet(**applet.dict()))


async def applet_versions_retrieve(
    applet_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session=Depends(session_manager.get_session),
) -> ResponseMulti[PublicHistory]:
    async with atomic(session):
        await AppletService(session, user.id).exist_by_id(applet_id)
        await CheckAccessService(session, user.id).check_applet_detail_access(
            applet_id
        )
        histories = await retrieve_versions(session, applet_id)
    return ResponseMulti(
        result=[PublicHistory(**h.dict()) for h in histories],
        count=len(histories),
    )


async def applet_version_retrieve(
    applet_id: uuid.UUID,
    version: str,
    user: User = Depends(get_current_user),
    session=Depends(session_manager.get_session),
) -> Response[public_history_detail.AppletDetailHistory]:
    async with atomic(session):
        await CheckAccessService(session, user.id).check_applet_detail_access(
            applet_id
        )
        applet = await retrieve_applet_by_version(session, applet_id, version)
    return Response(
        result=public_history_detail.AppletDetailHistory(**applet.dict())
    )


async def applet_version_changes_retrieve(
    applet_id: uuid.UUID,
    version: str,
    user: User = Depends(get_current_user),
    session=Depends(session_manager.get_session),
) -> Response[PublicAppletHistoryChange]:
    async with atomic(session):
        await CheckAccessService(session, user.id).check_applet_detail_access(
            applet_id
        )
        changes = await AppletHistoryService(
            session, applet_id, version
        ).get_changes()
    return Response(result=PublicAppletHistoryChange(**changes.dict()))


async def applet_delete(
    applet_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session=Depends(session_manager.get_session),
):
    async with atomic(session):
        service = AppletService(session, user.id)
        await service.exist_by_id(applet_id)
        await CheckAccessService(session, user.id).check_applet_delete_access(
            applet_id
        )
        await service.delete_applet_by_id(applet_id)


async def applet_set_folder(
    applet_folder: AppletFolder,
    user: User = Depends(get_current_user),
    session=Depends(session_manager.get_session),
):
    async with atomic(session):
        service = AppletService(session, user.id)
        await service.exist_by_id(applet_folder.applet_id)
        await CheckAccessService(session, user.id).check_applet_edit_access(
            applet_folder.applet_id
        )
        await service.set_applet_folder(applet_folder)


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
    applet_id: uuid.UUID,
    user: User = Depends(get_current_user),
    schema: CreateAccessLink = Body(...),
    session=Depends(session_manager.get_session),
) -> Response[AppletLink]:
    async with atomic(session):
        service = AppletService(session, user.id)
        await service.exist_by_id(applet_id)
        await CheckAccessService(session, user.id).check_link_edit_access(
            applet_id
        )
        access_link = await service.create_access_link(
            applet_id=applet_id, create_request=schema
        )
    return Response(result=access_link)


async def applet_link_get(
    applet_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session=Depends(session_manager.get_session),
) -> Response[AppletLink]:
    async with atomic(session):
        service = AppletService(session, user.id)
        await service.exist_by_id(applet_id)
        access_link = await service.get_access_link(applet_id=applet_id)
    return Response(result=access_link)


async def applet_link_delete(
    applet_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session=Depends(session_manager.get_session),
):
    async with atomic(session):
        service = AppletService(session, user.id)
        await service.exist_by_id(applet_id)
        await CheckAccessService(session, user.id).check_link_edit_access(
            applet_id
        )
        await service.delete_access_link(applet_id=applet_id)


async def applet_set_data_retention(
    applet_id: uuid.UUID,
    schema: AppletDataRetention,
    user: User = Depends(get_current_user),
    session=Depends(session_manager.get_session),
):
    async with atomic(session):
        await CheckAccessService(session, user.id).check_applet_edit_access(
            applet_id
        )
        await AppletService(session, user.id).set_data_retention(
            applet_id=applet_id, data_retention=schema
        )
