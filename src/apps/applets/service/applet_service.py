import re

from apps.activities.services.activity import ActivityService
from apps.activity_flows.service.flow import FlowService
from apps.applets.crud import AppletsCRUD, UserAppletAccessCRUD
from apps.applets.domain import (
    AppletDetail,
    AppletFolder,
    AppletInfo,
    AppletName,
    Role,
)
from apps.applets.errors import AppletAccessDenied, AppletsFolderAccessDenied
from apps.applets.service.user_applet_access import UserAppletAccessService
from apps.folders.crud import FolderCRUD

__all__ = ["AppletService"]

from apps.shared.query_params import QueryParams


class AppletService:
    INITIAL_VERSION = "1.0.0"
    VERSION_DIFFERENCE = 1
    APPLET_NAME_FORMAT_FOR_DUPLICATES = "{0} ({1})"

    # TODO: implement applet create/update logics here

    def __init__(self, user_id: int):
        self.user_id = user_id

    def get_next_version(self, version: str | None = None):
        if not version:
            return self.INITIAL_VERSION
        return ".".join(
            list(str(int(version.replace(".", "")) + self.VERSION_DIFFERENCE))
        )

    async def get_list_by_single_language(
        self, language: str, query_params: QueryParams
    ) -> list[AppletInfo]:
        roles: str = query_params.filters.pop("roles")

        schemas = await AppletsCRUD().get_applets_by_roles(
            self.user_id, roles.split(","), query_params
        )
        applets = []
        for schema in schemas:
            applets.append(
                AppletInfo(
                    id=schema.id,
                    display_name=schema.display_name,
                    version=schema.version,
                    description=self._get_by_language(
                        schema.description, language
                    ),
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
                )
            )
        return applets

    async def get_single_language_by_id(
        self, applet_id: int, language: str
    ) -> AppletDetail:
        roles = await UserAppletAccessCRUD().get_user_roles_to_applet(
            self.user_id, applet_id
        )
        if not roles:
            raise AppletAccessDenied()
        schema = await AppletsCRUD().get_applet_by_role(
            self.user_id, applet_id, Role.as_list()
        )
        applet = AppletDetail(
            id=schema.id,
            display_name=schema.display_name,
            version=schema.version,
            description=self._get_by_language(schema.description, language),
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
        )
        applet.activities = await ActivityService(
            self.user_id
        ).get_single_language_by_applet_id(applet_id, language)
        applet.activity_flows = (
            await FlowService().get_single_language_by_applet_id(
                applet_id, language
            )
        )
        return applet

    def get_prev_version(self, version: str):
        int_version = int(version.replace(".", ""))
        if int_version < int(self.INITIAL_VERSION.replace(".", "")):
            return self.INITIAL_VERSION
        return ".".join(list(str(int_version - self.VERSION_DIFFERENCE)))

    async def exist_by_id(self, applet_id: int) -> bool:
        return await AppletsCRUD().exist_by_id(applet_id)

    async def delete_applet_by_id(self, applet_id: int):
        await self._validate_delete_applet(self.user_id, applet_id)
        await AppletsCRUD().delete_by_id(applet_id)

    async def _validate_delete_applet(self, user_id, applet_id):
        role = await UserAppletAccessService(
            user_id, applet_id
        ).get_admins_role()
        if not role:
            raise AppletAccessDenied()

    async def get_single_language_by_folder_id(
        self, folder_id: int, language
    ) -> list[AppletInfo]:
        schemas = await AppletsCRUD().get_folder_applets(
            self.user_id, folder_id
        )
        applets = []
        for schema in schemas:
            applets.append(
                AppletInfo(
                    id=schema.id,
                    display_name=schema.display_name,
                    version=schema.version,
                    description=self._get_by_language(
                        schema.description, language
                    ),
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
                )
            )

        return applets

    async def set_applet_folder(self, schema: AppletFolder):
        if schema.folder_id:
            await self._move_to_folder(schema.applet_id, schema.folder_id)
        else:
            await self._remove_from_folder(schema.applet_id)

    async def _move_to_folder(self, applet_id: int, folder_id: int):
        await self._validate_applet(applet_id)
        await self._validate_folder(folder_id)
        await AppletsCRUD().set_applets_folder(applet_id, folder_id)

    async def _remove_from_folder(self, applet_id: int):
        await self._validate_applet(applet_id)
        await AppletsCRUD().set_applets_folder(applet_id, None)

    async def _validate_applet(self, applet_id: int):
        applet_schema = await AppletsCRUD().get_by_id(applet_id)
        if applet_schema.creator_id != self.user_id:
            raise AppletAccessDenied()

    async def _validate_folder(self, folder_id: int):
        folder = await FolderCRUD().get_by_id(folder_id)

        if folder.creator_id != self.user_id:
            raise AppletsFolderAccessDenied()

    async def get_unique_name(self, applet_name: AppletName) -> str:
        duplicate_names = await AppletsCRUD().get_name_duplicates(
            self.user_id, applet_name.name, applet_name.exclude_applet_id
        )
        if not duplicate_names:
            return applet_name.name

        greatest_number = 0
        for duplicate_name in duplicate_names:
            number = self._get_latest_number(duplicate_name)
            if number > greatest_number:
                greatest_number = number

        return self.APPLET_NAME_FORMAT_FOR_DUPLICATES.format(
            applet_name.name, greatest_number + 1
        )

    def _get_latest_number(self, text) -> int:
        numbers = re.findall("\\(\\d+\\)", text)
        if numbers:
            return int(numbers[-1][1:-1])
        return 0

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
