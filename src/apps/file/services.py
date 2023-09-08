import re
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from apps.file.dependencies import get_legacy_storage
from apps.file.storage import select_storage
from apps.workspaces.constants import StorageType
from apps.workspaces.crud.user_applet_access import UserAppletAccessCRUD
from apps.workspaces.domain.constants import Role
from apps.workspaces.service import workspace


def mongoid_to_uuid(id_):
    if isinstance(id_, str) and "/" in id_:
        id_ = id_.split("/").pop()
    return uuid.UUID(str(id_) + "00000000")


class BasePresignService:
    def __init__(self, session, user_id, applet_id, access):
        self.session = session
        self.user_id = user_id
        self.applet_id = applet_id
        self.access = access


class S3PresignService(BasePresignService):
    key_pattern = r"s3:\/\/[^\/]+\/"
    legacy_file_url_pattern = r"s3:\/\/[a-zA-Z0-9-]+\/[0-9a-fA-F]+\/[0-9a-fA-F]+\/[0-9a-fA-F]+(\/[a-zA-Z0-9.-]*)?"  # noqa
    regular_file_url_pattern = r"s3:\/\/[a-zA-Z0-9.-]+\/[a-zA-Z0-9-]+\/[a-zA-Z0-9-]+\/[a-f0-9-]+\/[a-f0-9-]+\/[a-zA-Z0-9-]+"  # noqa
    check_access_to_regular_url_pattern = (
        r"\/([0-9a-fA-F-]+)\/([0-9a-fA-F-]+)\/"
    )
    check_access_to_legacy_url_url_pattern = r"\/([0-9a-fA-F]+)\/"

    async def __call__(self, url):
        regular_cdn_client = await select_storage(
            applet_id=self.applet_id, session=self.session
        )

        arbitary_info = await workspace.WorkspaceService(
            self.session, self.user_id
        ).get_arbitrary_info(self.applet_id)

        legacy_cdn_client = (
            get_legacy_storage() if not arbitary_info else regular_cdn_client
        )

        if self._is_legacy_file_url_format(url):
            if not await self._check_access_to_legacy_url(url):
                return url
            key = self._get_key(url)
            return await legacy_cdn_client.generate_presigned_url(key)
        elif self._is_regular_file_url_format(url):
            if not await self._check_access_to_regular_url(url):
                return url
            key = self._get_key(url)
            return await regular_cdn_client.generate_presigned_url(key)
        else:
            return url

    def _get_key(self, url):
        pattern = self.key_pattern
        result = re.sub(pattern, "", url)
        return result

    def _is_legacy_file_url_format(self, url):
        pattern = self.legacy_file_url_pattern
        match = re.search(pattern, url)
        return bool(match)

    def _is_regular_file_url_format(self, url):
        pattern = self.regular_file_url_pattern
        match = re.search(pattern, url)
        return bool(match)

    async def _check_access_to_regular_url(self, url):
        pattern = self.check_access_to_regular_url_pattern
        match = re.search(pattern, url)
        user_id, applet_id = match.group(1), match.group(2)

        if self.user_id == user_id:
            return True

        if str(self.applet_id) != applet_id:
            return False

        if self.access:
            if self.access.role == Role.REVIEWER:
                return user_id in self.access.meta.get("respondents", [])
            return True
        return False

    async def _check_access_to_legacy_url(self, url):
        pattern = self.check_access_to_legacy_url_url_pattern
        match = re.search(pattern, url)
        applet_id = mongoid_to_uuid(match.group(1))

        if self.applet_id != applet_id:
            return False

        return bool(self.access)


class GCPPresignService(S3PresignService):
    key_pattern = r"gs:\/\/[^\/]+\/"
    legacy_file_url_pattern = r"gs:\/\/[a-zA-Z0-9-]+\/[0-9a-fA-F]+\/[0-9a-fA-F]+\/[0-9a-fA-F]+(\/[a-zA-Z0-9.-]*)?"  # noqa
    regular_file_url_pattern = r"gs:\/\/[a-zA-Z0-9.-]+\/[a-zA-Z0-9-]+\/[a-zA-Z0-9-]+\/[a-f0-9-]+\/[a-f0-9-]+\/[a-zA-Z0-9-]+"  # noqa

    def __call__(self, url):
        regular_cdn_client = await select_storage(
            applet_id=self.applet_id, session=self.session
        )

        if self._is_legacy_file_url_format(url):
            if not await self._check_access_to_legacy_url(url):
                return url
        elif self._is_regular_file_url_format(url):
            if not await self._check_access_to_regular_url(url):
                return url

        key = self._get_key(url)
        return await regular_cdn_client.generate_presigned_url(key)


class AzurePresignService(GCPPresignService):
    check_access_to_legacy_url_url_pattern = (
        r"\/([^/]+)\/[^/]+\/[^/]+\/[^/]+\.\w+"
    )
    check_access_to_regular_url_pattern = r"\/([0-9a-fA-F-]+)\/([0-9a-fA-F-]+)"

    def __call__(self, url):
        regular_cdn_client = await select_storage(
            applet_id=self.applet_id, session=self.session
        )

        key = None

        if self._is_legacy_file_url_format(url):
            if not await self._check_access_to_legacy_url(url):
                return url
            key = self._get_legacy_key(url)
        elif self._is_regular_file_url_format(url):
            if not await self._check_access_to_regular_url(url):
                return url
            key = self._get_regular_key(url)

        if key is None:
            return url

        return await regular_cdn_client.generate_presigned_url(key)

    def _get_legacy_key(self, url):
        pattern = (
            r"\/([0-9a-fA-F-]+\/[0-9a-fA-F-]+\/[0-9a-fA-F-]+\/[0-9a-zA-Z.-]+)$"
        )
        result = re.search(pattern, url)
        return result.group(1)

    def _get_regular_key(self, url):
        pattern = r"\/([0-9a-fA-F-]+\/[0-9a-fA-F-]+\/[a-zA-Z0-9.-]+\/[0-9]+)"
        result = re.search(pattern, url)
        return result.group(1)

    def _is_legacy_file_url_format(self, url):
        return ".net/mindlogger/" in url


class PresignedUrlsGeneratorService:
    def __init__(
        self, session: AsyncSession, user_id: uuid.UUID, applet_id: uuid.UUID
    ):
        self.session = session
        self.user_id = user_id
        self.applet_id = applet_id

    async def __call__(
        self,
        *,
        given_private_urls: list[str],
    ) -> list[str]:
        self.access = await UserAppletAccessCRUD(self.session).get_by_roles(
            self.user_id,
            self.applet_id,
            [Role.OWNER, Role.MANAGER, Role.REVIEWER, Role.RESPONDENT],
        )

        results = await self._generate_presigned_urls(
            given_private_urls=given_private_urls
        )
        return results

    async def _get_service(self):
        arbitary_info = await workspace.WorkspaceService(
            self.session, self.user_id
        ).get_arbitrary_info(self.applet_id)
        if not arbitary_info:
            return S3PresignService(
                self.session, self.user_id, self.applet_id, self.access
            )
        if arbitary_info.storage_type.lower() == StorageType.AZURE.value:
            return AzurePresignService(
                self.session, self.user_id, self.applet_id, self.access
            )
        if arbitary_info.storage_type.lower() == StorageType.GCP.value:
            return GCPPresignService(
                self.session, self.user_id, self.applet_id, self.access
            )

    async def _generate_presigned_urls(
        self,
        *,
        given_private_urls: list[str],
    ):
        urls = list()

        service = await self._get_service()

        for url in given_private_urls:
            url = await service(url)
            urls.append(url)

        return urls
