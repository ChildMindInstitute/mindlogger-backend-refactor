import re
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from apps.file.storage import get_legacy_storage, select_storage
from apps.migrate.utilities import mongoid_to_uuid
from apps.workspaces.crud.user_applet_access import UserAppletAccessCRUD
from apps.workspaces.domain.constants import Role
from config import settings


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
        results = await self._generate_presigned_urls(
            given_private_urls=given_private_urls
        )
        return results

    async def _check_access_to_regular_url(self, url):
        pattern = r"\/([0-9a-fA-F-]+)\/([0-9a-fA-F-]+)\/"
        match = re.search(pattern, url)
        user_id, applet_id = match.group(1), match.group(2)

        if str(self.applet_id) != applet_id:
            return False

        access = await UserAppletAccessCRUD(self.session).get_by_roles(
            self.user_id,
            self.applet_id,
            [Role.OWNER, Role.MANAGER, Role.REVIEWER],
        )

        if not access:
            return False

        if access.role == Role.REVIEWER:
            return user_id in access.meta.get("respondents", [])

    async def _check_access_to_legacy_url(self, url):
        pattern = r"\/([0-9a-fA-F]+)\/"
        match = re.search(pattern, url)
        applet_id = mongoid_to_uuid(match.group(1))

        if self.applet_id != applet_id:
            return False

        access = await UserAppletAccessCRUD(self.session).get_by_roles(
            self.user_id,
            self.applet_id,
            [Role.OWNER, Role.MANAGER, Role.REVIEWER],
        )

        return bool(access)

    def _remove_prefix(self, url):
        pattern = r"s3:\/\/[^\/]+\/"
        result = re.sub(pattern, "", url)
        return result

    def _is_legacy_file_url(self, url):
        return url.startswith(f"s3://{settings.cdn.legacy_bucket}")

    def _is_regular_file_url(self, url):
        return url.startswith(f"s3://{settings.cdn.bucket}")

    async def _generate_presigned_urls(
        self,
        *,
        given_private_urls: list[str],
    ):
        legacy_cdn_client = get_legacy_storage()
        regular_cdn_client = await select_storage(
            applet_id=self.applet_id, session=self.session
        )

        urls = []

        for url in given_private_urls:
            if self._is_legacy_file_url(url):
                if not await self._check_access_to_legacy_url(url):
                    urls.append(url)
                    continue
                urls.append(
                    legacy_cdn_client.generate_presigned_url(
                        self._remove_prefix(url)
                    )
                )
            elif self._is_regular_file_url(url):
                if not await self._check_access_to_regular_url(url):
                    urls.append(url)
                    continue
                urls.append(regular_cdn_client.generate_presigned_url(url))
            else:
                urls.append(url)

        return urls
