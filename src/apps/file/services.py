import re
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from apps.file.dependencies import get_legacy_storage
from apps.file.storage import select_storage
from apps.migrate.utilities import mongoid_to_uuid
from apps.workspaces.constants import StorageType
from apps.workspaces.crud.user_applet_access import UserAppletAccessCRUD
from apps.workspaces.domain.constants import Role
from apps.workspaces.service import workspace


class S3PresignService:
    def __init__(self, user_id, applet_id, access):
        self.user_id = user_id
        self.applet_id = applet_id
        self.access = access

    async def __call__(self, legacy_cdn_client, regular_cdn_client, url):
        if self._is_legacy_file_url_format(url):
            if not await self._check_access_to_legacy_url(url):
                return url
            url = self._get_legacy_key(url)
            return await legacy_cdn_client.generate_presigned_url(url)
        elif self._is_regular_file_url_format(url):
            if not await self._check_access_to_regular_url(url):
                return url
            url = self._get_legacy_key(url)
            return await regular_cdn_client.generate_presigned_url(url)
        else:
            return url

    def _get_legacy_key(self, url):
        pattern = r"s3:\/\/[^\/]+\/"
        result = re.sub(pattern, "", url)
        return result

    def _is_legacy_file_url_format(self, url):
        pattern = r"s3:\/\/[a-zA-Z0-9-]+\/[0-9a-fA-F]+\/[0-9a-fA-F]+\/[0-9a-fA-F]+(\/[a-zA-Z0-9.-]*)?"  # noqa
        match = re.search(pattern, url)
        return bool(match)

    def _is_regular_file_url_format(self, url):
        pattern = r"s3:\/\/[a-zA-Z0-9.-]+\/[a-zA-Z0-9-]+\/[a-zA-Z0-9-]+\/[a-f0-9-]+\/[a-f0-9-]+\/[a-zA-Z0-9-]+"  # noqa
        match = re.search(pattern, url)
        return bool(match)

    async def _check_access_to_regular_url(self, url):
        pattern = r"\/([0-9a-fA-F-]+)\/([0-9a-fA-F-]+)\/"
        match = re.search(pattern, url)
        user_id, applet_id = match.group(1), match.group(2)

        if self.user_id == mongoid_to_uuid(user_id):
            return True

        if str(self.applet_id) != applet_id:
            return False

        if self.access:
            if self.access.role == Role.REVIEWER:
                return user_id in self.access.meta.get("respondents", [])
            return True
        return False

    async def _check_access_to_legacy_url(self, url):
        pattern = r"\/([0-9a-fA-F]+)\/"
        match = re.search(pattern, url)
        applet_id = mongoid_to_uuid(match.group(1))

        if self.applet_id != applet_id:
            return False

        return bool(self.access)


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

    async def _generate_presigned_urls(
        self,
        *,
        given_private_urls: list[str],
    ):

        regular_cdn_client = await select_storage(
            applet_id=self.applet_id, session=self.session
        )

        arbitary_info = await workspace.WorkspaceService(
            self.session, self.user_id
        ).get_arbitrary_info(self.applet_id)

        urls = list()

        if arbitary_info and arbitary_info.storage_type.lower() in [
            StorageType.AZURE,
            StorageType.GCP,
        ]:
            for url in given_private_urls:
                url = await regular_cdn_client.generate_presigned_url(url)
                urls.append(url)
        else:
            legacy_cdn_client = (
                get_legacy_storage()
                if not arbitary_info
                else regular_cdn_client
            )
            presign_service = S3PresignService(
                self.user_id, self.applet_id, self.access
            )
            for url in given_private_urls:
                url = await presign_service(
                    legacy_cdn_client, regular_cdn_client, url
                )
                urls.append(url)

        return urls
