import re
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from apps.answers.service import get_user_migrated_answer_file_urls
from apps.file.domain import FilePresignedResponse
from apps.file.storage import get_legacy_storage, select_storage


class PresignedUrlsGeneratorService:
    async def __call__(
        self,
        *,
        session: AsyncSession,
        applet_id: uuid.UUID,
        given_private_urls: list[str],
    ) -> list[FilePresignedResponse]:
        legacy_cdn_client = get_legacy_storage()
        regular_cdn_client = await select_storage(
            applet_id=applet_id, session=session
        )

        migrated_private_urls = await get_user_migrated_answer_file_urls(
            session=session, applet_id=applet_id
        )
        legacy_private_urls, regular_private_urls = self._filter_urls(
            given_private_urls=given_private_urls,
            migrated_private_urls=migrated_private_urls,
        )

        return list(
            self._generate_presigned_urls(
                (legacy_cdn_client, regular_cdn_client),
                (legacy_private_urls, regular_private_urls),
            )
        )

    def _process_legacy_file_url(self, url):
        pattern = r"s3:\/\/[^\/]+\/"
        result = re.sub(pattern, "", url)
        return result

    def _filter_urls(
        self,
        *,
        given_private_urls: list[str],
        migrated_private_urls: list[str],
    ):
        legacy_private_urls = list()
        regular_private_urls = list()

        for private_url in given_private_urls:
            if private_url in migrated_private_urls:
                legacy_private_urls.append(
                    self._process_legacy_file_url(private_url)
                )
            else:
                regular_private_urls.append(private_url)

        return legacy_private_urls, regular_private_urls

    def _generate_presigned_urls(self, cdn_clients, urls):
        for cdn, urls in zip(cdn_clients, urls):
            for url in urls:
                yield FilePresignedResponse(
                    private_url=url, public_url=cdn.generate_presigned_url(url)
                )
