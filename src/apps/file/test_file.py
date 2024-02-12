import http
import io
import uuid
from unittest import mock

import pytest
from pytest_mock import MockerFixture
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Query

from apps.applets.domain.applet_full import AppletFull
from apps.file.enums import FileScopeEnum
from apps.file.services import LogFileService
from apps.shared.test import BaseTest
from apps.shared.test.client import TestClient
from apps.users.domain import User
from apps.workspaces.constants import StorageType
from apps.workspaces.db.schemas import UserWorkspaceSchema
from apps.workspaces.errors import AnswerViewAccessDenied
from config import settings
from infrastructure.utility.cdn_client import CDNClient
from infrastructure.utility.cdn_config import CdnConfig


async def set_storage_type(storage_type: str, session: AsyncSession):
    workspace_id = uuid.UUID("8b83d791-0d27-42c5-8b1d-e0c8d7faf808")
    query: Query = update(UserWorkspaceSchema)
    query = query.where(UserWorkspaceSchema.id == workspace_id)
    query = query.values(storage_type=storage_type)
    await session.execute(query)


@pytest.fixture
def mock_presigned_post(mocker: MockerFixture):
    def fake_generate_presigned_post(_, bucket: str, key: str, ExpiresIn=settings.cdn.ttl_signed_urls):
        return {
            "url": f"https://{bucket}.s3.amazonaws.com/",
            "fields": {
                "key": key,
                "AWSAccessKeyId": "accesskey",
                "policy": "policy",
                "signature": "signature",
            },
        }

    mock = mocker.patch("botocore.signers.generate_presigned_post", new=fake_generate_presigned_post)
    return mock


class TestAnswerActivityItems(BaseTest):
    fixtures = ["answers/fixtures/arbitrary_server_answers.json"]

    login_url = "/auth/login"
    upload_url = "file/{applet_id}/upload"
    download_url = "file/{applet_id}/download"
    existance_url = "/file/{applet_id}/upload/check"
    file_id = "1693560380000/c60859c4-6f5f-4390-a572-da85fcd59709"
    upload_media_url = "file/upload-url"
    answer_upload_url = "file/{applet_id}/upload-url"
    log_upload_url = "file/log-file/{device_id}/upload-url"

    @mock.patch("infrastructure.utility.cdn_arbitrary.ArbitraryS3CdnClient.upload")
    async def test_arbitrary_upload_to_s3_aws(
        self, mock_client: mock.MagicMock, session: AsyncSession, client: TestClient, applet_one: AppletFull
    ):
        await client.login(self.login_url, "tom@mindlogger.com", "Test1234!")
        await set_storage_type(StorageType.AWS, session)

        content = io.BytesIO(b"File content")
        response = await client.post(
            self.upload_url.format(applet_id=applet_one.id),
            query={"file_id": self.file_id},
            files={"file": content},
        )
        assert http.HTTPStatus.OK == response.status_code
        assert mock_client.call_count == 1

    @mock.patch(
        "infrastructure.utility.cdn_arbitrary.ArbitraryS3CdnClient.download",
        return_value=(iter(("a", "b")), "txt"),
    )
    async def test_arbitrary_download_from_s3_aws(
        self, mock_client: mock.MagicMock, session: AsyncSession, client: TestClient, applet_one: AppletFull
    ):
        await client.login(self.login_url, "tom@mindlogger.com", "Test1234!")
        await set_storage_type(StorageType.AWS, session)

        response = await client.post(
            self.download_url.format(applet_id=applet_one.id),
            data={"key": "key"},
        )
        assert http.HTTPStatus.OK == response.status_code
        assert mock_client.call_count == 1

    @mock.patch("infrastructure.utility.cdn_arbitrary.ArbitraryGCPCdnClient.upload")
    async def test_arbitrary_upload_to_s3_gcp(
        self, mock_client: mock.MagicMock, session: AsyncSession, client: TestClient, applet_one: AppletFull
    ):
        await client.login(self.login_url, "tom@mindlogger.com", "Test1234!")
        await set_storage_type(StorageType.GCP, session)
        content = io.BytesIO(b"File content")
        response = await client.post(
            self.upload_url.format(applet_id=applet_one.id),
            query={"file_id": self.file_id},
            files={"file": content},
        )
        assert http.HTTPStatus.OK == response.status_code
        assert mock_client.call_count == 1

    @mock.patch(
        "infrastructure.utility.cdn_arbitrary.ArbitraryGCPCdnClient.download",
        return_value=(iter(("a", "b")), "txt"),
    )
    async def test_arbitrary_download_from_s3_gcp(
        self, mock_client: mock.MagicMock, session: AsyncSession, client: TestClient, applet_one: AppletFull
    ):
        await client.login(self.login_url, "tom@mindlogger.com", "Test1234!")
        await set_storage_type(StorageType.GCP, session)

        response = await client.post(
            self.download_url.format(applet_id=applet_one.id),
            data={"key": "key"},
        )
        assert http.HTTPStatus.OK == response.status_code
        assert mock_client.call_count == 1

    @mock.patch("infrastructure.utility.cdn_arbitrary.ArbitraryAzureCdnClient.upload")
    @mock.patch("infrastructure.utility.cdn_arbitrary.ArbitraryAzureCdnClient.configure_client")
    async def test_arbitrary_upload_to_blob_azure(
        self,
        mock_configure_client: mock.MagicMock,
        mock_upload: mock.MagicMock,
        session: AsyncSession,
        client: TestClient,
        applet_one: AppletFull,
    ):
        await client.login(self.login_url, "tom@mindlogger.com", "Test1234!")
        await set_storage_type(StorageType.AZURE, session)
        content = io.BytesIO(b"File content")
        response = await client.post(
            self.upload_url.format(applet_id=applet_one.id),
            query={"file_id": self.file_id},
            files={"file": content},
        )
        assert http.HTTPStatus.OK == response.status_code
        assert mock_upload.call_count == 1

    @mock.patch("infrastructure.utility.cdn_arbitrary.CDNClient.check_existence")
    async def test_default_storage_check_existence(
        self, mock_client: mock.MagicMock, session: AsyncSession, client: TestClient, applet_one: AppletFull
    ):
        await client.login(self.login_url, "tom@mindlogger.com", "Test1234!")
        response = await client.post(
            self.existance_url.format(applet_id=applet_one.id),
            data={"files": [self.file_id]},
        )
        assert http.HTTPStatus.OK == response.status_code
        assert mock_client.call_count == 1

    @mock.patch("infrastructure.utility.cdn_arbitrary.ArbitraryS3CdnClient.check_existence")
    async def test_arbitary_s3_aws_check_existence(
        self, mock_client: mock.MagicMock, session: AsyncSession, client: TestClient, applet_one: AppletFull
    ):
        await client.login(self.login_url, "tom@mindlogger.com", "Test1234!")
        await set_storage_type(StorageType.AWS, session)
        response = await client.post(
            self.existance_url.format(applet_id=applet_one.id),
            data={"files": [self.file_id]},
        )
        assert http.HTTPStatus.OK == response.status_code
        assert mock_client.call_count == 1

    @pytest.mark.usefixtures("mock_presigned_post")
    @pytest.mark.parametrize("file_name,", ("test1.jpg", "test2.jpg"))
    async def test_generate_upload_url(self, client: TestClient, file_name: str):
        await client.login(self.login_url, "tom@mindlogger.com", "Test1234!")
        bucket_name = "testbucket"
        domain_name = "testdomain"
        settings.cdn.bucket = bucket_name
        settings.cdn.domain = domain_name
        resp = await client.post(self.upload_media_url, data={"file_name": file_name})
        assert resp.status_code == http.HTTPStatus.OK
        result = resp.json()["result"]
        assert result["fields"]["key"].endswith(file_name)
        assert result["url"] == settings.cdn.url.format(key=result["fields"]["key"])

    async def test_generate_presigned_url_for_post_answer__user_does_not_have_access_to_the_applet(
        self, client: TestClient, user: User, applet_one: AppletFull
    ):
        await client.login(self.login_url, user.email_encrypted, "Test1234!")
        resp = await client.post(self.answer_upload_url.format(applet_id=applet_one.id), data={"file_id": "test.txt"})
        assert resp.status_code == http.HTTPStatus.FORBIDDEN
        result = resp.json()["result"]
        assert len(result) == 1
        assert result[0]["message"] == AnswerViewAccessDenied.message

    @pytest.mark.usefixtures("mock_presigned_post")
    async def test_generate_presigned_url_for_answers(
        self, client: TestClient, tom: User, mocker: MockerFixture, applet_one: AppletFull
    ):
        await client.login(self.login_url, "tom@mindlogger.com", "Test1234!")
        file_id = "test.txt"
        expected_key = CDNClient.generate_key(FileScopeEnum.ANSWER, f"{tom.id}/{applet_one.id}", file_id)
        bucket_name = "bucket"
        settings.cdn.bucket = bucket_name
        settings.cdn.bucket_answer = bucket_name
        mocker.patch("apps.workspaces.service.workspace.WorkspaceService.get_arbitrary_info", return_value=None)
        resp = await client.post(self.answer_upload_url.format(applet_id=applet_one.id), data={"file_id": file_id})
        assert resp.status_code == http.HTTPStatus.OK
        assert resp.json()["result"]["fields"]["key"] == expected_key
        url = CDNClient(
            CdnConfig(region="region", bucket=bucket_name, secret_key="secret_key", access_key="access_key"), "env"
        ).generate_private_url(expected_key)
        assert resp.json()["result"]["url"] == url

    @pytest.mark.usefixtures("mock_presigned_post")
    async def test_generate_presigned_log_url(self, client: TestClient, device_tom: str, tom: User):
        await client.login(self.login_url, "tom@mindlogger.com", "Test1234!")
        file_name = "test.txt"
        resp = await client.post(self.log_upload_url.format(device_id=device_tom), data={"file_id": file_name})
        assert resp.status_code == http.HTTPStatus.OK
        key = resp.json()["result"]["fields"]["key"]
        expected_key = LogFileService(
            tom.id,
            CDNClient(
                CdnConfig(region="region", bucket="bucket", secret_key="secret_key", access_key="access_key"), "env"
            ),
        ).key(device_tom, file_name)
        assert key == expected_key
