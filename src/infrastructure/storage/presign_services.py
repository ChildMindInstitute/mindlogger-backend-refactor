import asyncio
import re
import uuid
from typing import Optional, List

from sqlalchemy.ext.asyncio import AsyncSession

from apps.workspaces.db.schemas import UserAppletAccessSchema
from apps.workspaces.domain.constants import Role
from apps.workspaces.service.workspace import WorkspaceService
from config import settings
from infrastructure.storage.cdn_client import CDNClient


def mongoid_to_uuid(id_):
    """Convert a MongoDB ObjectId to a UUID"""
    if isinstance(id_, str) and "/" in id_:
        id_ = id_.split("/").pop()
    return uuid.UUID(str(id_) + "00000000")


class S3PresignService:
    """
    Service to translate S3 URLs to presigned URLs for fetching non-public resources.
    Checks through a few mechanisms to determine whether the user has access to the requested resource
    depending on if it/they are a legacy or modern resource.
    """
    key_pattern = r"s3:\/\/[^\/]+\/"
    # Legacy URLs are in the format s3://<bucket>/<ObjectId>/<ObjectId>/<ObjectId>/<key>
    # Regular URLs are in the format s3://<bucket>/mindlogger/answer/<uuid>/<uuid>/<key>
    legacy_file_url_pattern = r"s3:\/\/[a-zA-Z0-9-]+\/[0-9a-fA-F]+\/[0-9a-fA-F]+\/[0-9a-fA-F]+(\/[a-zA-Z0-9.-]*)?"  # noqa
    regular_file_url_pattern = (
        r"s3:\/\/[a-zA-Z0-9.-]+\/[a-zA-Z0-9-]+\/[a-zA-Z0-9-]+\/[a-f0-9-]+\/[a-f0-9-]+\/[a-zA-Z0-9-]+"  # noqa
    )

    # Regular URLS are UUIDs that contain hyphens, legacy URLS are Mongo IDs (ObjectID) that do not contain hyphens.
    check_access_to_regular_url_pattern = r"\/([0-9a-fA-F-]+)\/([0-9a-fA-F-]+)\/"
    check_access_to_legacy_url_pattern = r"\/([0-9a-fA-F]+)\/([0-9a-fA-F]+)\/"

    def __init__(
        self,
        session: AsyncSession,
        user_id: uuid.UUID,
        applet_id: uuid.UUID,
        access: UserAppletAccessSchema | None,
        cdn_client: CDNClient,
    ):
        self.session = session
        self.user_id = user_id
        self.applet_id = applet_id
        self.access = access
        self.cdn_client = cdn_client


    async def _presign(self, url: str | None) -> Optional[str]:
        """Presign a URL if the location is not public"""
        if not url:
            return None

        if self._is_legacy_file_url_format(url):
            if not await self._check_access_to_legacy_url(url):
                return url
            key = self._get_key(url)

            # Legacy assets were moved to the current answer bucket with a prefix.  Append it to the key.
            if settings.cdn.legacy_prefix:
                key = f"{settings.cdn.legacy_prefix}/{key}"

            return await self.cdn_client.generate_presigned_url(key)

        elif self._is_regular_file_url_format(url):
            if not await self._check_access_to_regular_url(url):
                return url
            key = self._get_key(url)
            return await self.cdn_client.generate_presigned_url(key)
        else:
            return url

    async def presign(self, urls: List[str | None]) -> List[str | None]:
        c_list = []

        for url in urls:
            c_list.append(self._presign(url))
        result = await asyncio.gather(*c_list)
        return result

    def _get_key(self, url: str) -> str:
        """Parse the key from a URL string in the format s3://<bucket>/<key>"""
        pattern = self.key_pattern
        result = re.sub(pattern, "", url)
        return result

    def _is_legacy_file_url_format(self, url):
        """Is the given URL in the legacy format?"""
        match = re.search(self.legacy_file_url_pattern, url)
        return bool(match)

    def _is_regular_file_url_format(self, url):
        """Is the given URL in the regular format?"""
        match = re.search(self.regular_file_url_pattern, url)
        return bool(match)

    async def _check_access_to_regular_url(self, url) -> bool:
        """
        Checks whether the user has access to the provided regular URL.

        This method validates the user's access to a specified URL based on the provided
        URL pattern and user-related properties. It checks whether the user ID in the URL
        matches the current user, whether the applet ID aligns with the given value, and
        whether the user's existing access level permits access to the requested resource.

        Arguments:
            url: The regular URL string to check access permissions for.

        Returns:
            A boolean indicating whether the user has access to the given URL.
        """
        pattern = self.check_access_to_regular_url_pattern
        match = re.search(pattern, url)
        user_id, applet_id = match.group(1), match.group(2)

        if self.user_id == user_id:
            return True

        if str(self.applet_id) != applet_id:
            return False

        if self.access and self.access.role != Role.RESPONDENT:
            return True

        return False

    async def _check_access_to_legacy_url(self, url) -> bool:
        """
        Checks whether the user has access to the provided legacy URL.

        This method validates the user's access to a specified URL based on the provided
        URL pattern and user-related properties. It checks whether the applet ID aligns
        with the given value, and whether the user's existing access level permits access
        to the requested resource.

        Arguments:
            url: The legacy URL string to check access permissions for.

        Returns:
            A boolean indicating whether the user has access to the given URL.
        """
        pattern = self.check_access_to_legacy_url_pattern
        match = re.search(pattern, url)
        if not match:
            return False
        applet_id = mongoid_to_uuid(match.group(2))

        if self.applet_id != applet_id:
            return False

        return bool(self.access)


class GCPPresignService(S3PresignService):
    key_pattern = r"gs:\/\/[^\/]+\/"
    legacy_file_url_pattern = r"gs:\/\/[a-zA-Z0-9-]+\/[0-9a-fA-F]+\/[0-9a-fA-F]+\/[0-9a-fA-F]+(\/[a-zA-Z0-9.-]*)?"  # noqa
    regular_file_url_pattern = (
        r"gs:\/\/[a-zA-Z0-9.-]+\/[a-zA-Z0-9-]+\/[a-zA-Z0-9-]+\/[a-f0-9-]+\/[a-f0-9-]+\/[a-zA-Z0-9-]+"  # noqa
    )

    async def _presign(self, url: str | None, *kwargs):
        # regular_cdn_client = await select_storage(applet_id=self.applet_id, session=self.session)
        if not url:
            return None

        if self._is_legacy_file_url_format(url):
            if not await self._check_access_to_legacy_url(url):
                return url
        elif self._is_regular_file_url_format(url):
            if not await self._check_access_to_regular_url(url):
                return url

        key = self._get_key(url)

        return await self.cdn_client.generate_presigned_url(key)


class AzurePresignService(GCPPresignService):
    check_access_to_legacy_url_pattern = r"\/[0-9a-fA-F-]+\/([0-9a-fA-F-]+)\/[0-9a-fA-F-]+\/"
    check_access_to_regular_url_pattern = r"\/([0-9a-fA-F-]+)\/([0-9a-fA-F-]+)"

    async def __call__(self, url):
        # regular_cdn_client = await select_storage(applet_id=self.applet_id, session=self.session)
        if self._is_legacy_file_url_format(url):
            if not await self._check_access_to_legacy_url(url):
                return url
            key = self._get_legacy_key(url)
        elif self._is_regular_file_url_format(url):
            if not await self._check_access_to_regular_url(url):
                return url
            key = self._get_regular_key(url)
        else:
            return url
        return await self.cdn_client.generate_presigned_url(key)

    @staticmethod
    def _get_legacy_key(url):
        pattern = r"\/([0-9a-fA-F-]+\/[0-9a-fA-F-]+\/[0-9a-fA-F-]+\/[0-9a-zA-Z.-]+)$"
        result = re.search(pattern, url)
        return result.group(1)

    @staticmethod
    def _get_regular_key(url):
        pattern = r"\/([0-9a-fA-F-]+\/[0-9a-fA-F-]+\/[a-zA-Z0-9.-]+\/[0-9]+)"
        result = re.search(pattern, url)
        return result.group(1)

    def _is_legacy_file_url_format(self, url):
        return ".net/mindlogger/" in url and ".net/mindlogger/answer/" not in url

    def _is_regular_file_url_format(self, url):
        return ".net/mindlogger/answer/" in url
