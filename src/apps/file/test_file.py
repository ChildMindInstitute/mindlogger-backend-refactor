import io
import uuid
from unittest import mock

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Query

from apps.shared.test import BaseTest
from apps.workspaces.constants import StorageType
from apps.workspaces.db.schemas import UserWorkspaceSchema
from infrastructure.database import rollback_with_session


async def set_storage_type(storage_type: str, session: AsyncSession):
    workspace_id = uuid.UUID("8b83d791-0d27-42c5-8b1d-e0c8d7faf808")
    query: Query = update(UserWorkspaceSchema)
    query = query.where(UserWorkspaceSchema.id == workspace_id)
    query = query.values(storage_type=storage_type)  # noqa
    await session.execute(query)


class TestAnswerActivityItems(BaseTest):
    fixtures = ["answers/fixtures/arbitrary_server_answers.json"]

    login_url = "/auth/login"
    upload_url = "file/{applet_id}/upload"
    download_url = "file/{applet_id}/download"
    applet_id = "92917a56-d586-4613-b7aa-991f2c4b15b8"

    @rollback_with_session
    @mock.patch("infrastructure.utility.cdn_arbitrary.CdnClientS3.upload")
    async def test_arbitrary_upload_to_s3_aws(
        self, mock_client: mock.MagicMock, **kwargs
    ):
        await self.client.login(
            self.login_url, "ivan@mindlogger.com", "Test1234!"
        )
        await set_storage_type(StorageType.AWS, kwargs["session"])

        content = io.BytesIO(b"File content")
        response = await self.client.post(
            self.upload_url.format(applet_id=self.applet_id),
            files={"file": content},
        )
        assert 200 == response.status_code
        assert mock_client.call_count == 1

    @rollback_with_session
    @mock.patch(
        "infrastructure.utility.cdn_arbitrary.CdnClientS3.download",
        return_value=(iter(("a", "b")), "txt"),
    )
    async def test_arbitrary_download_from_s3_aws(
        self, mock_client: mock.MagicMock, **kwargs
    ):
        await self.client.login(
            self.login_url, "ivan@mindlogger.com", "Test1234!"
        )
        await set_storage_type(StorageType.AWS, kwargs["session"])

        response = await self.client.post(
            self.download_url.format(applet_id=self.applet_id),
            data={"key": "key"},
        )
        assert 200 == response.status_code
        assert mock_client.call_count == 1

    @rollback_with_session
    @mock.patch("infrastructure.utility.cdn_arbitrary.CdnClientS3.upload")
    async def test_arbitrary_upload_to_s3_gcp(
        self, mock_client: mock.MagicMock, **kwargs
    ):
        await self.client.login(
            self.login_url, "ivan@mindlogger.com", "Test1234!"
        )
        await set_storage_type(StorageType.GCP, kwargs["session"])
        content = io.BytesIO(b"File content")
        response = await self.client.post(
            self.upload_url.format(applet_id=self.applet_id),
            files={"file": content},
        )
        assert 200 == response.status_code
        assert mock_client.call_count == 1

    @rollback_with_session
    @mock.patch(
        "infrastructure.utility.cdn_arbitrary.CdnClientS3.download",
        return_value=(iter(("a", "b")), "txt"),
    )
    async def test_arbitrary_download_from_s3_gcp(
        self, mock_client: mock.MagicMock, **kwargs
    ):
        await self.client.login(
            self.login_url, "ivan@mindlogger.com", "Test1234!"
        )
        await set_storage_type(StorageType.GCP, kwargs["session"])

        response = await self.client.post(
            self.download_url.format(applet_id=self.applet_id),
            data={"key": "key"},
        )
        assert 200 == response.status_code
        assert mock_client.call_count == 1

    @rollback_with_session
    @mock.patch("infrastructure.utility.cdn_arbitrary.CdnClientBlob.upload")
    async def test_arbitrary_upload_to_blob_azure(
        self, mock_client: mock.MagicMock, **kwargs
    ):
        await self.client.login(
            self.login_url, "ivan@mindlogger.com", "Test1234!"
        )
        await set_storage_type(StorageType.AZURE, kwargs["session"])
        content = io.BytesIO(b"File content")
        response = await self.client.post(
            self.upload_url.format(applet_id=self.applet_id),
            files={"file": content},
        )
        assert 200 == response.status_code
        assert mock_client.call_count == 1
