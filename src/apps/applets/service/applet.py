import asyncio
import re
import uuid

from apps.activities.crud import ActivitiesCRUD, ActivityItemsCRUD
from apps.activities.domain.activity_create import ActivityCreate, ActivityItemCreate
from apps.activities.services.activity import ActivityService
from apps.activity_flows.crud import FlowsCRUD
from apps.activity_flows.domain.flow_create import FlowCreate, FlowItemCreate
from apps.activity_flows.service.flow import FlowService
from apps.answers.crud.answers import AnswersCRUD
from apps.applets.crud import AppletHistoriesCRUD, AppletsCRUD, UserAppletAccessCRUD
from apps.applets.db.schemas import AppletSchema
from apps.applets.domain import (
    AppletActivitiesBaseInfo,
    AppletFolder,
    AppletName,
    AppletSingleLanguageDetail,
    AppletSingleLanguageInfo,
    Role,
)
from apps.applets.domain.applet import Applet, AppletDataRetention
from apps.applets.domain.applet_create_update import AppletCreate, AppletReportConfiguration, AppletUpdate
from apps.applets.domain.applet_duplicate import AppletDuplicate
from apps.applets.domain.applet_full import AppletFull
from apps.applets.domain.applet_link import AppletLink, CreateAccessLink
from apps.applets.domain.base import Encryption
from apps.applets.errors import (
    AccessLinkDoesNotExistError,
    AppletAlreadyExist,
    AppletLinkAlreadyExist,
    AppletNotFoundError,
    AppletsFolderAccessDenied,
)
from apps.applets.service.applet_history_service import AppletHistoryService
from apps.folders.crud import FolderAppletCRUD, FolderCRUD
from apps.schedule.service import ScheduleService
from apps.shared.version import (
    INITIAL_VERSION,
    VERSION_DIFFERENCE_ACTIVITY,
    VERSION_DIFFERENCE_ITEM,
    VERSION_DIFFERENCE_MINOR,
)
from apps.themes.service import ThemeService
from apps.users.services.user import UserService
from apps.workspaces.errors import AppletEncryptionUpdateDenied
from apps.workspaces.service.user_applet_access import UserAppletAccessService
from config import settings

__all__ = [
    "AppletService",
    "PublicAppletService",
]

from apps.shared.query_params import QueryParams
from infrastructure.utility import FCMNotification, FirebaseMessage, FirebaseNotificationType


class AppletService:
    APPLET_NAME_FORMAT_FOR_DUPLICATES = "{0} ({1})"

    # TODO: implement applet create/update logics here

    def __init__(self, session, user_id: uuid.UUID):
        self.user_id = user_id
        self.session = session

    async def exist_by_id(self, applet_id: uuid.UUID):
        exists = await AppletsCRUD(self.session).exist_by_key("id", applet_id)
        if not exists:
            raise AppletNotFoundError(key="id", value=str(applet_id))

    async def exist_by_ids(self, applet_ids: list[uuid.UUID]):
        exists = await AppletsCRUD(self.session).exist_by_ids(ids=applet_ids)
        if not exists:
            raise AppletNotFoundError(key="id", value=str(applet_ids))

    async def get(self, applet_id: uuid.UUID):
        applet = await AppletsCRUD(self.session).get_by_id(applet_id)
        if not applet:
            raise AppletNotFoundError(key="id", value=str(applet_id))

        return applet

    async def exist_by_key(self, applet_id: uuid.UUID):
        exists = await AppletsCRUD(self.session).exist_by_key("link", applet_id)
        if not exists:
            raise AppletNotFoundError(key="link", value=str(applet_id))

    async def _create_applet_accesses(
        self,
        applet_id: uuid.UUID,
        manager_id: uuid.UUID | None,
        manager_role: Role | None = None,
    ):
        if manager_role is None:
            manager_role = Role.MANAGER
        # TODO: move to api level
        await UserAppletAccessService(self.session, self.user_id, applet_id).add_role(self.user_id, Role.OWNER)

        await UserAppletAccessService(self.session, self.user_id, applet_id).add_role(self.user_id, Role.RESPONDENT)

        if manager_id and manager_id != self.user_id:
            await UserAppletAccessService(self.session, self.user_id, applet_id).add_role(manager_id, manager_role)

            await UserAppletAccessService(self.session, self.user_id, applet_id).add_role(manager_id, Role.RESPONDENT)

    async def create(
        self,
        create_data: AppletCreate,
        manager_id: uuid.UUID | None = None,
        manager_role: Role | None = None,
        applet_id: uuid.UUID = uuid.uuid4(),
    ) -> AppletFull:
        applet = await self._create(create_data, manager_id or self.user_id, applet_id=applet_id)

        await self._create_applet_accesses(applet.id, manager_id, manager_role)

        applet.activities = await ActivityService(self.session, self.user_id).create(applet.id, create_data.activities)
        activity_key_id_map = dict()
        for activity in applet.activities:
            activity_key_id_map[activity.key] = activity.id
        applet.activity_flows = await FlowService(self.session).create(
            applet.id, create_data.activity_flows, activity_key_id_map
        )

        await AppletHistoryService(self.session, applet.id, applet.version).add_history(
            manager_id or self.user_id, applet
        )

        return applet

    async def _create(
        self, create_data: AppletCreate, creator_id: uuid.UUID, applet_id: uuid.UUID = uuid.uuid4()
    ) -> AppletFull:
        await self._validate_applet_name(create_data.display_name)
        if not create_data.theme_id:
            theme = await ThemeService(self.session, self.user_id).get_default()
            create_data.theme_id = theme.id
        schema = await AppletsCRUD(self.session).save(
            AppletSchema(
                id=applet_id,
                display_name=create_data.display_name,
                description=create_data.description,
                about=create_data.about,
                image=create_data.image,
                watermark=create_data.watermark,
                theme_id=create_data.theme_id,
                version=await self.get_next_version(),
                report_server_ip=create_data.report_server_ip,
                report_public_key=create_data.report_public_key,
                report_recipients=create_data.report_recipients,
                report_include_user_id=create_data.report_include_user_id,
                report_include_case_id=create_data.report_include_case_id,
                report_email_body=create_data.report_email_body,
                encryption=create_data.encryption.dict() if create_data.encryption else None,
                extra_fields=create_data.extra_fields,
                creator_id=creator_id,
            )
        )
        return AppletFull.from_orm(schema)

    async def update(self, applet_id: uuid.UUID, update_data: AppletUpdate) -> AppletFull:
        old_applet_schema = await AppletsCRUD(self.session).get_by_id(applet_id)

        next_version = await self.get_next_version(old_applet_schema.version, update_data, applet_id)

        await FlowService(self.session).remove_applet_flows(applet_id)
        await ActivityService(self.session, self.user_id).remove_applet_activities(applet_id)
        applet = await self._update(applet_id, update_data, next_version)
        applet.activities = await ActivityService(self.session, self.user_id).update_create(
            applet_id, update_data.activities
        )
        activity_key_id_map = dict()
        activity_ids = []
        assessment_id = None
        for activity in applet.activities:
            activity_key_id_map[activity.key] = activity.id
            activity_ids.append(activity.id)
            if activity.is_reviewable:
                assessment_id = activity.id
        applet.activity_flows = await FlowService(self.session).update_create(
            applet_id, update_data.activity_flows, activity_key_id_map
        )

        await AppletHistoryService(self.session, applet.id, applet.version).add_history(self.user_id, applet)

        event_serv = ScheduleService(self.session)
        to_await = []
        if assessment_id:
            to_await.append(event_serv.delete_by_activity_ids(applet_id, [assessment_id]))
        to_await.append(
            event_serv.create_default_schedules_if_not_exist(
                applet_id=applet.id,
                activity_ids=activity_ids,
            )
        )
        await asyncio.gather(*to_await)
        return applet

    async def update_encryption(self, applet_id: uuid.UUID, encryption: Encryption):
        applet = await AppletsCRUD(self.session).get_by_id(applet_id)
        if applet.encryption is not None:
            raise AppletEncryptionUpdateDenied()

        applet.encryption = encryption.dict()
        await AppletsCRUD(self.session).save(applet)

    async def duplicate(
        self,
        applet_exist: AppletDuplicate,
        new_name: str,
        encryption: Encryption,
    ):
        activity_key_id_map = dict()

        await self._validate_applet_name(new_name)
        applet_owner = await UserAppletAccessCRUD(self.session).get_applet_owner(applet_exist.id)

        has_editor = await UserAppletAccessCRUD(self.session).check_access_by_user_and_owner(
            user_id=self.user_id,
            owner_id=applet_owner.user_id,
            roles=[Role.EDITOR],
        )
        manager_role = Role.EDITOR if has_editor else Role.MANAGER

        create_data = self._prepare_duplicate(applet_exist, new_name, encryption)

        applet = await self._create(create_data, self.user_id)
        # TODO: move to api level
        await UserAppletAccessService(self.session, applet_owner.user_id, applet.id).add_role(
            applet_owner.user_id, Role.OWNER
        )
        await UserAppletAccessService(self.session, applet_owner.user_id, applet.id).add_role(
            applet_owner.user_id, Role.RESPONDENT
        )

        if self.user_id != applet_owner.user_id:
            await UserAppletAccessService(self.session, applet_owner.user_id, applet.id).add_role(
                self.user_id, manager_role
            )
            await UserAppletAccessService(self.session, applet_owner.user_id, applet.id).add_role(
                self.user_id, Role.RESPONDENT
            )

        applet.activities = await ActivityService(self.session, applet_owner.user_id).create(
            applet.id, create_data.activities
        )
        for activity in applet.activities:
            activity_key_id_map[activity.key] = activity.id
        applet.activity_flows = await FlowService(self.session).create(
            applet.id, create_data.activity_flows, activity_key_id_map
        )

        await AppletHistoryService(self.session, applet.id, applet.version).add_history(self.user_id, applet)

        return applet

    @staticmethod
    def _prepare_duplicate(applet_exist: AppletDuplicate, new_name: str, encryption: Encryption) -> AppletCreate:
        activities = list()
        for activity in applet_exist.activities:
            activities.append(
                ActivityCreate(
                    name=activity.name,
                    key=activity.key,
                    description=activity.description,
                    splash_screen=activity.splash_screen,
                    image=activity.image,
                    show_all_at_once=activity.show_all_at_once,
                    is_skippable=activity.is_skippable,
                    is_reviewable=activity.is_reviewable,
                    response_is_editable=activity.response_is_editable,
                    items=[ActivityItemCreate.from_orm(item) for item in activity.items],
                    is_hidden=activity.is_hidden,
                    report_included_item_name=activity.report_included_item_name,  # noqa: E501
                    subscale_setting=activity.subscale_setting,
                    scores_and_reports=activity.scores_and_reports,
                )
            )

        activity_flows = list()
        for activity_flow in applet_exist.activity_flows:
            activity_flows.append(
                FlowCreate(
                    name=activity_flow.name,
                    description=activity_flow.description,
                    is_single_report=activity_flow.is_single_report,
                    hide_badge=activity_flow.hide_badge,
                    is_hidden=activity_flow.is_hidden,
                    items=[FlowItemCreate(activity_key=item) for item in activity_flow.activity_ids],
                    report_included_activity_name=activity_flow.report_included_activity_name,  # noqa: E501
                    report_included_item_name=activity_flow.report_included_item_name,  # noqa: E501
                )
            )

        return AppletCreate(
            display_name=new_name,
            description=applet_exist.description,
            about=applet_exist.about,
            image=applet_exist.image,
            watermark=applet_exist.watermark,
            theme_id=applet_exist.theme_id,
            activities=activities,
            activity_flows=activity_flows,
            encryption=encryption,
        )

    async def _validate_applet_name(self, display_name: str, exclude_by_id: uuid.UUID | None = None):
        applet_ids_query = UserAppletAccessCRUD(self.session).user_applet_ids_query(self.user_id)
        existed_applet = await AppletsCRUD(self.session).get_by_display_name(
            display_name, applet_ids_query, exclude_by_id
        )
        if existed_applet:
            raise AppletAlreadyExist()

    async def _update(self, applet_id: uuid.UUID, update_data: AppletUpdate, version: str) -> AppletFull:
        await self._validate_applet_name(update_data.display_name, applet_id)

        schema = await AppletsCRUD(self.session).update_by_id(
            applet_id,
            AppletSchema(
                display_name=update_data.display_name,
                description=update_data.description,
                encryption=update_data.encryption.dict() if update_data.encryption else None,
                about=update_data.about,
                image=update_data.image,
                watermark=update_data.watermark,
                theme_id=update_data.theme_id,
                version=version,
                stream_enabled=update_data.stream_enabled,
                stream_ip_address=update_data.stream_ip_address,
                stream_port=update_data.stream_port,
            ),
        )
        return AppletFull.from_orm(schema)

    async def get_next_version(
        self,
        version: str | None = None,
        applet_schema: AppletUpdate | None = None,
        applet_id: uuid.UUID | None = None,
    ):
        if not version:
            return INITIAL_VERSION

        if applet_schema and applet_id:
            version_difference = await self._get_next_version(applet_schema, applet_id)
        else:
            version_difference = VERSION_DIFFERENCE_MINOR

        version_parts = version.split(".")
        major_version = int(version_parts[0])
        middle_version = int(version_parts[1])
        minor_version = int(version_parts[2])

        if version_difference == VERSION_DIFFERENCE_MINOR:
            minor_version += 1
        elif version_difference == VERSION_DIFFERENCE_ACTIVITY:
            major_version += 1
            middle_version = 0
            minor_version = 0
        elif version_difference == VERSION_DIFFERENCE_ITEM:
            middle_version += 1
            minor_version = 0

        return f"{major_version}.{middle_version}.{minor_version}"

    async def _get_next_version(self, applet_schema: AppletUpdate, applet_id: uuid.UUID):
        old_activity_ids = set(await ActivitiesCRUD(self.session).get_ids_by_applet_id(applet_id))
        old_flow_ids = set(await FlowsCRUD(self.session).get_ids_by_applet_id(applet_id))
        new_activity_ids = set(activity.id for activity in applet_schema.activities)
        new_flow_ids = set(flow.id for flow in applet_schema.activity_flows)

        if new_activity_ids != old_activity_ids or new_flow_ids != old_flow_ids:
            return VERSION_DIFFERENCE_ACTIVITY
        else:
            old_activity_items_ids = set(
                await ActivityItemsCRUD(self.session).get_ids_by_activity_ids(list(old_activity_ids))
            )

            new_activity_items = []
            for new_activity in applet_schema.activities:
                new_activity_items.extend(new_activity.items)

            new_activity_items_ids = set(item.id for item in new_activity_items)
            if new_activity_items_ids != old_activity_items_ids:
                return VERSION_DIFFERENCE_ITEM
            else:
                return VERSION_DIFFERENCE_MINOR

    async def get_list_by_single_language(
        self, language: str, query_params: QueryParams
    ) -> list[AppletSingleLanguageInfo]:
        roles: str = query_params.filters.pop("roles")
        # Exclude edge case when after transfering applets ownership
        # applet can be shown in applet list for owner in mobile or web
        # without encryption
        schemas = await AppletsCRUD(self.session).get_applets_by_roles(
            self.user_id,
            list(map(Role, roles.split(","))),
            query_params,
            exclude_without_encryption=True,
        )
        theme_ids = [schema.theme_id for schema in schemas if schema.theme_id]
        themes = []
        if theme_ids:
            themes = await ThemeService(self.session, self.user_id).get_by_ids(theme_ids)
            pass
        theme_map = dict((theme.id, theme) for theme in themes)
        applets = []

        for schema in schemas:
            theme = theme_map.get(schema.theme_id)
            applets.append(
                AppletSingleLanguageInfo(
                    id=schema.id,
                    encryption=schema.encryption,
                    display_name=schema.display_name,
                    version=schema.version,
                    description=self._get_by_language(schema.description, language),
                    theme=theme.dict() if theme else None,
                    about=self._get_by_language(schema.about, language),
                    image=schema.image,
                    watermark=schema.watermark,
                    theme_id=schema.theme_id,
                    report_server_ip=schema.report_server_ip,
                    report_public_key=schema.report_public_key,
                    report_recipients=schema.report_recipients,
                    report_include_user_id=schema.report_include_user_id,
                    report_include_case_id=schema.report_include_case_id,
                    report_email_body=schema.report_email_body,
                    created_at=schema.created_at,
                    updated_at=schema.updated_at,
                    stream_enabled=schema.stream_enabled,
                    stream_ip_address=schema.stream_ip_address,
                    stream_port=schema.stream_port,
                )
            )
        return applets

    async def get_list_by_single_language_count(self, query_params: QueryParams) -> int:
        roles: str = query_params.filters.pop("roles")
        count = await AppletsCRUD(self.session).get_applets_by_roles_count(
            self.user_id,
            roles.split(","),
            query_params,
            exclude_without_encryption=True,
        )
        return count

    async def get_single_language_by_id(self, applet_id: uuid.UUID, language: str) -> AppletSingleLanguageDetail:
        schema = await AppletsCRUD(self.session).get_by_id(applet_id)
        theme = None
        if schema.theme_id:
            theme = await ThemeService(self.session, self.user_id).get_by_id(schema.theme_id)
        applet = AppletSingleLanguageDetail(
            id=schema.id,
            encryption=schema.encryption,
            display_name=schema.display_name,
            version=schema.version,
            description=self._get_by_language(schema.description, language),
            about=self._get_by_language(schema.about, language),
            image=schema.image,
            theme=theme.dict() if theme else None,
            watermark=schema.watermark,
            theme_id=schema.theme_id,
            report_server_ip=schema.report_server_ip,
            report_public_key=schema.report_public_key,
            report_recipients=schema.report_recipients,
            report_include_user_id=schema.report_include_user_id,
            report_include_case_id=schema.report_include_case_id,
            report_email_body=schema.report_email_body,
            created_at=schema.created_at,
            updated_at=schema.updated_at,
            retention_period=schema.retention_period,
            retention_type=schema.retention_type,
            is_published=schema.is_published,
            stream_enabled=schema.stream_enabled,
            stream_ip_address=schema.stream_ip_address,
            stream_port=schema.stream_port,
        )
        activities = ActivityService(self.session, self.user_id).get_single_language_by_applet_id(applet_id, language)
        activity_flows = FlowService(self.session).get_single_language_by_applet_id(applet_id, language)
        futures = await asyncio.gather(activities, activity_flows)
        applet.activities = futures[0]
        applet.activity_flows = futures[1]
        return applet

    async def get_single_language_by_key(self, key: uuid.UUID, language: str) -> AppletSingleLanguageDetail:
        schema = await AppletsCRUD(self.session).get_by_key(key)
        if not schema:
            raise AppletNotFoundError(key="key", value=str(key))
        theme = None
        if schema.theme_id:
            theme = await ThemeService(self.session, self.user_id).get_by_id(schema.theme_id)
        applet = AppletSingleLanguageDetail(
            id=schema.id,
            display_name=schema.display_name,
            version=schema.version,
            encryption=schema.encryption,
            description=self._get_by_language(schema.description, language),
            about=self._get_by_language(schema.about, language),
            image=schema.image,
            theme=theme.dict() if theme else None,
            watermark=schema.watermark,
            theme_id=schema.theme_id,
            report_server_ip=schema.report_server_ip,
            report_public_key=schema.report_public_key,
            report_recipients=schema.report_recipients,
            report_include_user_id=schema.report_include_user_id,
            report_include_case_id=schema.report_include_case_id,
            report_email_body=schema.report_email_body,
            created_at=schema.created_at,
            updated_at=schema.updated_at,
            retention_period=schema.retention_period,
            retention_type=schema.retention_type,
        )

        applet.activities = await ActivityService(self.session, self.user_id).get_single_language_by_applet_id(
            applet.id, language
        )
        applet.activity_flows = await FlowService(self.session).get_single_language_by_applet_id(applet.id, language)
        return applet

    async def get_by_id_for_duplicate(self, applet_id: uuid.UUID) -> AppletDuplicate:
        schema = await AppletsCRUD(self.session).get_by_id(applet_id)
        theme = None
        if schema.theme_id:
            theme = await ThemeService(self.session, self.user_id).get_users_by_id(schema.theme_id)
        applet = AppletDuplicate(
            id=schema.id,
            encryption=None,
            display_name=schema.display_name,
            version=schema.version,
            description=schema.description,
            about=schema.about,
            image=schema.image,
            theme=theme.dict() if theme else None,
            watermark=schema.watermark,
            theme_id=schema.theme_id,
            report_server_ip=schema.report_server_ip,
            report_public_key=schema.report_public_key,
            report_recipients=schema.report_recipients,
            report_include_user_id=schema.report_include_user_id,
            report_include_case_id=schema.report_include_case_id,
            report_email_body=schema.report_email_body,
            created_at=schema.created_at,
            updated_at=schema.updated_at,
            retention_period=schema.retention_period,
            retention_type=schema.retention_type,
        )
        applet.activities = await ActivityService(self.session, self.user_id).get_by_applet_id_for_duplicate(applet_id)
        applet.activity_flows = await FlowService(self.session).get_by_applet_id_duplicate(applet_id)
        return applet

    async def delete_applet_by_id(self, applet_id: uuid.UUID):
        await AppletsCRUD(self.session).get_by_id(applet_id)
        await AnswersCRUD(self.session).delete_by_applet_user(applet_id)
        await UserAppletAccessCRUD(self.session).delete_all_by_applet_id(applet_id)
        await AppletsCRUD(self.session).delete_by_id(applet_id)
        await FolderAppletCRUD(self.session).delete_folder_applet_by_applet_id(applet_id)

    async def set_applet_folder(self, schema: AppletFolder):
        if schema.folder_id:
            await self._move_to_folder(schema.applet_id, schema.folder_id)
        else:
            await self._remove_from_folder(schema.applet_id)

    async def _move_to_folder(self, applet_id: uuid.UUID, folder_id: uuid.UUID):
        await AppletsCRUD(self.session).get_by_id(applet_id)
        await self._validate_folder(folder_id)
        access = await UserAppletAccessCRUD(self.session).get_applet_owner(applet_id)

        await FolderCRUD(self.session).set_applet_folder(access.user_id, self.user_id, applet_id, folder_id)

    async def _remove_from_folder(self, applet_id: uuid.UUID):
        await AppletsCRUD(self.session).get_by_id(applet_id)
        access = await UserAppletAccessCRUD(self.session).get_applet_owner(applet_id)
        await FolderCRUD(self.session).set_applet_folder(access.user_id, self.user_id, applet_id, None)

    async def _validate_folder(self, folder_id: uuid.UUID):
        folder = await FolderCRUD(self.session).get_by_id(folder_id)

        if folder.creator_id != self.user_id:
            raise AppletsFolderAccessDenied()

    async def get_unique_name(self, applet_name: AppletName) -> str:
        duplicate_names = await AppletsCRUD(self.session).get_name_duplicates(
            self.user_id, applet_name.name, applet_name.exclude_applet_id
        )
        if not duplicate_names:
            return applet_name.name

        greatest_number = 0
        for duplicate_name in duplicate_names:
            number = self._get_latest_number(duplicate_name)
            if number > greatest_number:
                greatest_number = number

        return self.APPLET_NAME_FORMAT_FOR_DUPLICATES.format(applet_name.name, greatest_number + 1)

    async def get_unique_name_for_duplicate(self, name: str) -> str:
        duplicate_names = await AppletsCRUD(self.session).get_name_duplicates(self.user_id, name)
        if not duplicate_names:
            return name

        greatest_number = 0
        for duplicate_name in duplicate_names:
            number = self._get_latest_number(duplicate_name)
            if number > greatest_number:
                greatest_number = number

        return self.APPLET_NAME_FORMAT_FOR_DUPLICATES.format(name, greatest_number + 1)

    def _get_latest_number(self, text) -> int:
        numbers = re.findall("\\(\\d+\\)", text)
        if numbers:
            return int(numbers[-1][1:-1])
        return 0

    async def create_access_link(self, applet_id: uuid.UUID, create_request: CreateAccessLink) -> AppletLink:
        applet = await AppletsCRUD(self.session).get_by_id(applet_id)
        if applet.link:
            raise AppletLinkAlreadyExist()

        applet_link = await AppletsCRUD(self.session).create_access_link(applet_id, create_request.require_login)
        link = self._generate_link_url(create_request.require_login, applet_link)
        if not create_request.require_login:
            await UserService(self.session).create_anonymous_respondent()
            await UserAppletAccessService(self.session, self.user_id, applet_id).add_role_for_anonymous_respondent()
        return AppletLink(link=link, require_login=create_request.require_login)

    async def get_access_link(self, applet_id: uuid.UUID) -> AppletLink:
        applet = await AppletsCRUD(self.session).get_by_id(applet_id)
        if applet.link:
            link = self._generate_link_url(bool(applet.require_login), str(applet.link))
        else:
            raise AccessLinkDoesNotExistError

        return AppletLink(link=link, require_login=applet.require_login)

    async def delete_access_link(self, applet_id: uuid.UUID):
        applet = await AppletsCRUD(self.session).get_by_id(applet_id)
        if not applet.link:
            raise AccessLinkDoesNotExistError

        await AppletsCRUD(self.session).delete_access_link(applet_id)

    def _generate_link_url(self, require_login: bool, link: str) -> str:
        if require_login:
            url_path = settings.service.urls.frontend.private_link
        else:
            url_path = settings.service.urls.frontend.public_link

        domain = settings.service.urls.frontend.web_base

        url = f"https://{domain}/{url_path}/{str(link)}"

        return url

    @staticmethod
    def _get_by_language(values: dict, language: str):
        """
        Returns value by language key,
         if it does not exist,
         returns first existing or empty string
        """
        try:
            return values[language]
        except KeyError:
            for key, val in values.items():
                return val
            return ""

    async def set_data_retention(self, applet_id: uuid.UUID, data_retention: AppletDataRetention):
        await AppletsCRUD(self.session).set_data_retention(applet_id, data_retention)

    async def get_full_applet(self, applet_id: uuid.UUID) -> AppletFull:
        schema = await AppletsCRUD(self.session).get_by_id(applet_id)
        applet = AppletFull.from_orm(schema)
        applet.activities = await ActivityService(self.session, self.user_id).get_full_activities(applet_id)
        applet.activity_flows = await FlowService(self.session).get_full_flows(applet_id)
        return applet

    async def publish(self, applet_id: uuid.UUID):
        await AppletsCRUD(self.session).publish_by_id(applet_id)

    async def conceal(self, applet_id: uuid.UUID):
        await AppletsCRUD(self.session).conceal_by_id(applet_id)

    async def set_report_configuration(self, applet_id: uuid.UUID, schema: AppletReportConfiguration):
        repository = AppletsCRUD(self.session)
        applet = await repository.get_by_id(applet_id)
        await repository.set_report_configuration(applet_id, schema)
        await AppletHistoriesCRUD(self.session).set_report_configuration(applet.id, applet.version, schema)

    async def send_notification_to_applet_respondents(
        self,
        applet_id: uuid.UUID,
        title,
        body,
        type_: FirebaseNotificationType,
        *,
        device_ids: list | None = None,
        respondent_ids: list | None = None,
    ):
        if device_ids is None:
            device_ids = []
        respondents_device_ids = await AppletsCRUD(self.session).get_respondents_device_ids(applet_id, respondent_ids)
        respondents_device_ids += device_ids
        await FCMNotification().notify(
            respondents_device_ids,
            FirebaseMessage(
                title=title,
                body=body,
                data=dict(
                    type=type_,
                    applet_id=applet_id,
                ),
            ),
        )

    async def get_info_by_id(self, applet_id: uuid.UUID, language: str) -> AppletActivitiesBaseInfo:
        schema = await AppletsCRUD(self.session).get_by_id(applet_id)
        return await self._get_info_by_id(schema, language)

    async def get_info_by_key(self, key: uuid.UUID, language: str) -> AppletActivitiesBaseInfo:
        schema = await AppletsCRUD(self.session).get_by_key(key)
        return await self._get_info_by_id(schema, language)

    async def _get_info_by_id(self, schema: AppletSchema, language: str) -> AppletActivitiesBaseInfo:
        applet = AppletActivitiesBaseInfo(
            id=schema.id,
            display_name=schema.display_name,
            version=schema.version,
            description=self._get_by_language(schema.description, language),
            about=self._get_by_language(schema.about, language),
            image=schema.image,
            watermark=schema.watermark,
            created_at=schema.created_at,
            updated_at=schema.updated_at,
            activities=[],
            activity_flows=[],
        )
        activities = ActivityService(self.session, self.user_id).get_info_by_applet_id(schema.id, language)
        activity_flows = FlowService(self.session).get_info_by_applet_id(schema.id, language)
        futures = await asyncio.gather(activities, activity_flows)
        applet.activities = futures[0]
        applet.activity_flows = futures[1]
        return applet


class PublicAppletService:
    def __init__(self, session):
        self.session = session

    async def get_by_link(self, link: uuid.UUID, is_private=False) -> Applet | None:
        schema = await AppletsCRUD(self.session).get_by_link(link, is_private)
        if not schema:
            return None
        return Applet.from_orm(schema)
