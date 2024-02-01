import io
import uuid
from unittest import mock

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Query

from apps.shared.test import BaseTest
from apps.workspaces.constants import StorageType
from apps.workspaces.db.schemas import UserWorkspaceSchema


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
    existance_url = "/file/{applet_id}/upload/check"
    applet_id = "92917a56-d586-4613-b7aa-991f2c4b15b8"
    file_id = "1693560380000/c60859c4-6f5f-4390-a572-da85fcd59709"

    @mock.patch("infrastructure.utility.cdn_arbitrary.ArbitraryS3CdnClient.upload")
    async def test_arbitrary_upload_to_s3_aws(self, mock_client: mock.MagicMock, session, client, **kwargs):
        await client.login(self.login_url, "ivan@mindlogger.com", "Test1234!")
        await set_storage_type(StorageType.AWS, session)

        content = io.BytesIO(b"File content")
        response = await client.post(
            self.upload_url.format(applet_id=self.applet_id),
            query={"file_id": self.file_id},
            files={"file": content},
        )
        assert 200 == response.status_code
        assert mock_client.call_count == 1

    @mock.patch(
        "infrastructure.utility.cdn_arbitrary.ArbitraryS3CdnClient.download",
        return_value=(iter(("a", "b")), "txt"),
    )
    async def test_arbitrary_download_from_s3_aws(self, mock_client: mock.MagicMock, session, client, **kwargs):
        await client.login(self.login_url, "ivan@mindlogger.com", "Test1234!")
        await set_storage_type(StorageType.AWS, session)

        response = await client.post(
            self.download_url.format(applet_id=self.applet_id),
            data={"key": "key"},
        )
        assert 200 == response.status_code
        assert mock_client.call_count == 1

    @mock.patch("infrastructure.utility.cdn_arbitrary.ArbitraryGCPCdnClient.upload")
    async def test_arbitrary_upload_to_s3_gcp(self, mock_client: mock.MagicMock, session, client, **kwargs):
        await client.login(self.login_url, "ivan@mindlogger.com", "Test1234!")
        await set_storage_type(StorageType.GCP, session)
        content = io.BytesIO(b"File content")
        response = await client.post(
            self.upload_url.format(applet_id=self.applet_id),
            query={"file_id": self.file_id},
            files={"file": content},
        )
        assert 200 == response.status_code
        assert mock_client.call_count == 1

    @mock.patch(
        "infrastructure.utility.cdn_arbitrary.ArbitraryGCPCdnClient.download",
        return_value=(iter(("a", "b")), "txt"),
    )
    async def test_arbitrary_download_from_s3_gcp(self, mock_client: mock.MagicMock, session, client, **kwargs):
        await client.login(self.login_url, "ivan@mindlogger.com", "Test1234!")
        await set_storage_type(StorageType.GCP, session)

        response = await client.post(
            self.download_url.format(applet_id=self.applet_id),
            data={"key": "key"},
        )
        assert 200 == response.status_code
        assert mock_client.call_count == 1

    @mock.patch("infrastructure.utility.cdn_arbitrary.ArbitraryAzureCdnClient.upload")
    @mock.patch(
        "infrastructure.utility.cdn_arbitrary.ArbitraryAzureCdnClient.configure_client"  # noqa
    )
    async def test_arbitrary_upload_to_blob_azure(
        self,
        mock_configure_client: mock.MagicMock,
        mock_upload: mock.MagicMock,
        session,
        client,
        *args,
        **kwargs,
    ):
        await client.login(self.login_url, "ivan@mindlogger.com", "Test1234!")
        await set_storage_type(StorageType.AZURE, session)
        content = io.BytesIO(b"File content")
        response = await client.post(
            self.upload_url.format(applet_id=self.applet_id),
            query={"file_id": self.file_id},
            files={"file": content},
        )
        assert 200 == response.status_code
        assert mock_upload.call_count == 1

    @mock.patch("infrastructure.utility.cdn_arbitrary.CDNClient.check_existence")
    async def test_default_storage_check_existence(self, mock_client: mock.MagicMock, session, client, **kwargs):
        await client.login(self.login_url, "ivan@mindlogger.com", "Test1234!")
        response = await client.post(
            self.existance_url.format(applet_id=self.applet_id),
            data={"files": [self.file_id]},
        )
        assert 200 == response.status_code
        assert mock_client.call_count == 1

    @mock.patch(
        "infrastructure.utility.cdn_arbitrary.ArbitraryS3CdnClient.check_existence"  # noqa
    )
    async def test_arbitary_s3_aws_check_existence(self, mock_client: mock.MagicMock, session, client, **kwargs):
        await client.login(self.login_url, "ivan@mindlogger.com", "Test1234!")
        await set_storage_type(StorageType.AWS, session)
        response = await client.post(
            self.existance_url.format(applet_id=self.applet_id),
            data={"files": [self.file_id]},
        )
        assert 200 == response.status_code
        assert mock_client.call_count == 1
