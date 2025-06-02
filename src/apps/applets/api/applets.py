import asyncio
import uuid
from copy import deepcopy

from fastapi import Body, Depends
from firebase_admin.exceptions import FirebaseError
from starlette.responses import Response as HTTPResponse

from apps.activities.crud import ActivitiesCRUD
from apps.activities.domain.activity_update import ActivityReportConfiguration
from apps.activities.services.activity import ActivityService
from apps.activity_flows.domain.flow_update import ActivityFlowReportConfiguration
from apps.activity_flows.service.flow import FlowService
from apps.applets.crud import AppletsCRUD, UserAppletAccessCRUD
from apps.applets.domain import AppletFolder, AppletName, AppletUniqueName, PublicAppletHistoryChange, PublicHistory
from apps.applets.domain.applet import (
    AppletActivitiesBaseInfo,
    AppletDataRetention,
    AppletMeta,
    AppletRetrieveResponse,
    AppletSingleLanguageDetailForPublic,
    AppletSingleLanguageDetailPublic,
    AppletSingleLanguageInfoPublic,
)
from apps.applets.domain.applet_create_update import (
    AppletCreate,
    AppletDuplicateRequest,
    AppletReportConfiguration,
    AppletUpdate,
)
from apps.applets.domain.applet_history import VersionPublic
from apps.applets.domain.applet_link import AppletLink, CreateAccessLink
from apps.applets.domain.applets import public_detail, public_history_detail
from apps.applets.domain.base import Encryption
from apps.applets.filters import AppletQueryParams, FlowItemHistoryExportQueryParams
from apps.applets.service import AppletHistoryService, AppletService
from apps.applets.service.applet_history import retrieve_applet_by_version, retrieve_versions
from apps.authentication.deps import get_current_user
from apps.shared.domain.response import Response, ResponseMulti
from apps.shared.exception import NotFoundError
from apps.shared.link import convert_link_key
from apps.shared.query_params import QueryParams, parse_query_params
from apps.subjects.services import SubjectsService
from apps.users.domain import User
from apps.workspaces.domain.constants import Role
from apps.workspaces.service.check_access import CheckAccessService
from infrastructure.database import atomic
from infrastructure.database.deps import get_session
from infrastructure.http import get_language
from infrastructure.logger import logger

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

from infrastructure.utility.notification_client import FirebaseNotificationType


async def applet_list(
    user: User = Depends(get_current_user),
    language: str = Depends(get_language),
    query_params: QueryParams = Depends(parse_query_params(AppletQueryParams)),
    session=Depends(get_session),
) -> ResponseMulti[AppletSingleLanguageInfoPublic]:
    async with atomic(session):
        applets = await AppletService(session, user.id).get_list_by_single_language(language, deepcopy(query_params))
        count = await AppletService(session, user.id).get_list_by_single_language_count(deepcopy(query_params))
    return ResponseMulti(
        result=[AppletSingleLanguageInfoPublic.from_orm(applet) for applet in applets],
        count=count,
    )


async def applet_retrieve(
    applet_id: uuid.UUID,
    user: User = Depends(get_current_user),
    language: str = Depends(get_language),
    session=Depends(get_session),
) -> AppletRetrieveResponse[AppletSingleLanguageDetailPublic]:
    async with atomic(session):
        service = AppletService(session, user.id)
        await service.exist_by_id(applet_id)
        await CheckAccessService(session, user.id).check_applet_detail_access(applet_id)
        applet_future = service.get_single_language_by_id(applet_id, language)
        subject_future = SubjectsService(session, user.id).get_by_user_and_applet(user.id, applet_id)
        has_assessment_future = AppletService(session, user.id).has_assessment(applet_id)
        applet, subject, has_assessment = await asyncio.gather(applet_future, subject_future, has_assessment_future)
        applet_owner = await UserAppletAccessCRUD(session).get_applet_owner(applet_id)
        applet.owner_id = applet_owner.owner_id
    return AppletRetrieveResponse(
        result=AppletSingleLanguageDetailPublic.from_orm(applet),
        respondent_meta=SubjectsService.to_respondent_meta(subject),
        applet_meta=AppletMeta(has_assessment=has_assessment),
    )


async def applet_retrieve_by_key(
    key: str,
    language: str = Depends(get_language),
    session=Depends(get_session),
) -> Response[AppletSingleLanguageDetailForPublic]:
    key_guid = convert_link_key(key)
    async with atomic(session):
        service = AppletService(session, uuid.UUID("00000000-0000-0000-0000-000000000000"))
        await service.exist_by_key(key_guid)
        applet = await service.get_single_language_by_key(key_guid, language)
    return Response(result=AppletSingleLanguageDetailForPublic.from_orm(applet))


async def applet_create(
    owner_id: uuid.UUID,
    user: User = Depends(get_current_user),
    schema: AppletCreate = Body(...),
    session=Depends(get_session),
) -> Response[public_detail.Applet]:
    async with atomic(session):
        await CheckAccessService(session, user.id).check_applet_create_access(owner_id)
        has_editor = await UserAppletAccessCRUD(session).check_access_by_user_and_owner(
            user_id=user.id, owner_id=owner_id, roles=[Role.EDITOR]
        )
        manager_role = Role.EDITOR if has_editor else None
        applet = await AppletService(session, owner_id).create(schema, user.id, manager_role)
    return Response(result=public_detail.Applet.from_orm(applet))


async def applet_update(
    applet_id: uuid.UUID,
    user: User = Depends(get_current_user),
    schema: AppletUpdate = Body(...),
    session=Depends(get_session),
) -> Response[public_detail.Applet]:
    async with atomic(session):
        service = AppletService(session, user.id)
        await service.exist_by_id(applet_id)
        await CheckAccessService(session, user.id).check_applet_edit_access(applet_id)
        applet = await service.update(applet_id, schema)
    try:
        await service.send_notification_to_applet_respondents(
            applet_id,
            "Applet is updated.",
            "Applet is updated.",
            FirebaseNotificationType.APPLET_UPDATE,
        )
    except FirebaseError as e:
        # mute error
        logger.exception(e)

    return Response(result=public_detail.Applet.from_orm(applet))


async def applet_encryption_update(
    applet_id: uuid.UUID,
    user: User = Depends(get_current_user),
    schema: Encryption = Body(...),
    session=Depends(get_session),
) -> Response[public_detail.Encryption]:
    async with atomic(session):
        service = AppletService(session, user.id)
        await service.exist_by_id(applet_id)
        await CheckAccessService(session, user.id).check_applet_edit_access(applet_id)
        await service.update_encryption(applet_id, schema)
    return Response(result=public_detail.Encryption.from_orm(schema))


async def applet_duplicate(
    applet_id: uuid.UUID,
    user: User = Depends(get_current_user),
    schema: AppletDuplicateRequest = Body(...),
    session=Depends(get_session),
) -> Response[public_detail.Applet]:
    async with atomic(session):
        service = AppletService(session, user.id)
        await service.exist_by_id(applet_id)
        await CheckAccessService(session, user.id).check_applet_duplicate_access(applet_id)
        applet_for_duplicate = await service.get_by_id_for_duplicate(applet_id)

        applet = await service.duplicate(
            applet_for_duplicate, schema.display_name, schema.encryption, schema.include_report_server
        )
    return Response(result=public_detail.Applet.from_orm(applet))


async def applet_set_report_configuration(
    applet_id: uuid.UUID,
    user: User = Depends(get_current_user),
    schema: AppletReportConfiguration = Body(...),
    session=Depends(get_session),
):
    async with atomic(session):
        service = AppletService(session, user.id)
        await service.exist_by_id(applet_id)
        await CheckAccessService(session, user.id).check_applet_edit_access(applet_id)
        await service.set_report_configuration(applet_id, schema)


async def flow_report_config_update(
    applet_id: uuid.UUID,
    flow_id: uuid.UUID,
    user: User = Depends(get_current_user),
    schema: ActivityFlowReportConfiguration = Body(...),
    session=Depends(get_session),
):
    service = FlowService(session, admin_user_id=user.id)
    await AppletService(session, user.id).exist_by_id(applet_id)
    await CheckAccessService(session, user.id).check_applet_edit_access(applet_id)
    flow = await service.get_by_id(flow_id)
    if not flow or flow.applet_id != applet_id:
        raise NotFoundError()

    async with atomic(session):
        await service.update_report_config(flow_id, schema)

    return HTTPResponse()


async def activity_report_config_update(
    applet_id: uuid.UUID,
    activity_id: uuid.UUID,
    schema: ActivityReportConfiguration = Body(...),
    user: User = Depends(get_current_user),
    session=Depends(get_session),
):
    await AppletService(session, user.id).exist_by_id(applet_id)
    await CheckAccessService(session, user.id).check_applet_edit_access(applet_id)

    activity = await ActivitiesCRUD(session).get_by_id(activity_id)
    if not activity or activity.applet_id != applet_id:
        raise NotFoundError()

    async with atomic(session):
        await ActivityService(session, user.id).update_report(activity_id, schema)

    return HTTPResponse()


async def applet_publish(
    applet_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session=Depends(get_session),
):
    async with atomic(session):
        service = AppletService(session, user.id)
        await service.exist_by_id(applet_id)
        await CheckAccessService(session, user.id, user.is_super_admin).check_publish_conceal_access()
        await service.publish(applet_id)


async def applet_conceal(
    applet_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session=Depends(get_session),
):
    async with atomic(session):
        service = AppletService(session, user.id)
        await service.exist_by_id(applet_id)
        await CheckAccessService(session, user.id, user.is_super_admin).check_publish_conceal_access()
        await service.conceal(applet_id)


async def applet_versions_retrieve(
    applet_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session=Depends(get_session),
) -> ResponseMulti[PublicHistory]:
    async with atomic(session):
        await AppletService(session, user.id).exist_by_id(applet_id)
        await CheckAccessService(session, user.id).check_applet_detail_access(applet_id)
        histories = await retrieve_versions(session, applet_id)
    return ResponseMulti(
        result=[PublicHistory(**h.dict()) for h in histories],
        count=len(histories),
    )


async def applet_flow_versions_data_retrieve(
    applet_id: uuid.UUID,
    flow_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session=Depends(get_session),
) -> ResponseMulti[VersionPublic]:
    await AppletService(session, user.id).exist_by_id(applet_id)
    await CheckAccessService(session, user.id).check_applet_detail_access(applet_id)
    service = FlowService(session=session, admin_user_id=user.id)
    versions = await service.get_versions(applet_id, flow_id)
    return ResponseMulti(
        result=versions,
        count=len(versions),
    )


async def applet_version_retrieve(
    applet_id: uuid.UUID,
    version: str,
    user: User = Depends(get_current_user),
    session=Depends(get_session),
) -> Response[public_history_detail.AppletDetailHistory]:
    async with atomic(session):
        await AppletService(session, user.id).exist_by_id(applet_id)
        await CheckAccessService(session, user.id).check_applet_detail_access(applet_id)
        applet = await retrieve_applet_by_version(session, applet_id, version)
    return Response(result=public_history_detail.AppletDetailHistory(**applet.dict()))


async def applet_version_changes_retrieve(
    applet_id: uuid.UUID,
    version: str,
    user: User = Depends(get_current_user),
    session=Depends(get_session),
) -> Response[PublicAppletHistoryChange]:
    async with atomic(session):
        await AppletService(session, user.id).exist_by_id(applet_id)
        await CheckAccessService(session, user.id).check_applet_detail_access(applet_id)
        changes = await AppletHistoryService(session, applet_id, version).get_changes()
    return Response(result=PublicAppletHistoryChange(**changes.dict()))


async def applet_delete(
    applet_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session=Depends(get_session),
):
    async with atomic(session):
        service = AppletService(session, user.id)
        await service.exist_by_id(applet_id)
        await CheckAccessService(session, user.id).check_applet_delete_access(applet_id)
        respondents_device_ids = await AppletsCRUD(session).get_respondents_device_ids(applet_id)
        await service.delete_applet_by_id(applet_id)
    try:
        await service.send_notification_to_applet_respondents(
            applet_id,
            "Applet is deleted.",
            "Applet is deleted.",
            FirebaseNotificationType.APPLET_DELETE,
            device_ids=respondents_device_ids,
        )
    except FirebaseError as e:
        # mute error
        logger.exception(e)


async def applet_set_folder(
    applet_folder: AppletFolder,
    user: User = Depends(get_current_user),
    session=Depends(get_session),
):
    async with atomic(session):
        service = AppletService(session, user.id)
        await service.exist_by_id(applet_folder.applet_id)
        await CheckAccessService(session, user.id).check_applet_edit_access(applet_folder.applet_id)
        await service.set_applet_folder(applet_folder)


async def applet_unique_name_get(
    schema: AppletName = Body(...),
    user: User = Depends(get_current_user),
    session=Depends(get_session),
) -> Response[AppletUniqueName]:
    async with atomic(session):
        new_name = await AppletService(session, user.id).get_unique_name(schema)
    return Response(result=AppletUniqueName(name=new_name))


async def applet_link_create(
    applet_id: uuid.UUID,
    user: User = Depends(get_current_user),
    schema: CreateAccessLink = Body(...),
    session=Depends(get_session),
) -> Response[AppletLink]:
    async with atomic(session):
        service = AppletService(session, user.id)
        await service.exist_by_id(applet_id)
        await CheckAccessService(session, user.id).check_link_edit_access(applet_id)
        access_link = await service.create_access_link(applet_id=applet_id, create_request=schema)
    return Response(result=access_link)


async def applet_link_get(
    applet_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session=Depends(get_session),
) -> Response[AppletLink]:
    async with atomic(session):
        service = AppletService(session, user.id)
        await service.exist_by_id(applet_id)
        access_link = await service.get_access_link(applet_id=applet_id)
    return Response(result=access_link)


async def applet_link_delete(
    applet_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session=Depends(get_session),
):
    async with atomic(session):
        service = AppletService(session, user.id)
        await service.exist_by_id(applet_id)
        await CheckAccessService(session, user.id).check_link_edit_access(applet_id)
        await service.delete_access_link(applet_id=applet_id)


async def applet_set_data_retention(
    applet_id: uuid.UUID,
    schema: AppletDataRetention,
    user: User = Depends(get_current_user),
    session=Depends(get_session),
):
    async with atomic(session):
        service = AppletService(session, user.id)
        await service.exist_by_id(applet_id)
        await CheckAccessService(session, user.id).check_applet_retention_access(applet_id)
        await service.set_data_retention(applet_id, schema)


async def applet_retrieve_base_info(
    applet_id: uuid.UUID,
    language: str = Depends(get_language),
    user: User = Depends(get_current_user),
    session=Depends(get_session),
) -> Response[AppletActivitiesBaseInfo]:
    service = AppletService(session, user.id)
    await service.exist_by_id(applet_id)
    await CheckAccessService(session, user.id).check_applet_detail_access(applet_id)
    applet = await service.get_info_by_id(applet_id, language)

    return Response(result=AppletActivitiesBaseInfo.from_orm(applet))


async def applet_retrieve_base_info_by_key(
    key: str,
    language: str = Depends(get_language),
    session=Depends(get_session),
) -> Response[AppletSingleLanguageDetailForPublic]:
    key_guid = convert_link_key(key)
    service = AppletService(session, uuid.UUID("00000000-0000-0000-0000-000000000000"))
    await service.exist_by_key(key_guid)
    applet = await service.get_info_by_key(key_guid, language)
    return Response(result=AppletActivitiesBaseInfo.from_orm(applet))


async def flow_item_history(
    applet_id: uuid.UUID,
    user: User = Depends(get_current_user),
    query_params: QueryParams = Depends(parse_query_params(FlowItemHistoryExportQueryParams)),
    session=Depends(get_session),
):
    async with atomic(session):
        await AppletService(session, user.id).exist_by_id(applet_id)
        await CheckAccessService(session, user.id).check_applet_detail_access(applet_id)

        events_history, total = await AppletService(
            session,
            user.id,
        ).get_flow_history(applet_id, query_params)

    return ResponseMulti(result=events_history, count=total)
