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
from apps.file.domain import WebmTargetExtenstion
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

# This id is getting from JSON fixtures for answers
WORKSPACE_ARBITRARY_ID = uuid.UUID("8b83d791-0d27-42c5-8b1d-e0c8d7faf808")
ARBITRARY_BUCKET_NAME = "arbitrary_bucket"


async def set_storage_type(storage_type: str, session: AsyncSession):
    query: Query = update(UserWorkspaceSchema)
    query = query.where(UserWorkspaceSchema.id == WORKSPACE_ARBITRARY_ID)
    if storage_type == StorageType.AWS:
        query = query.values(storage_type=storage_type, storage_bucket=ARBITRARY_BUCKET_NAME)
    else:
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
        mocker.patch(
            "apps.workspaces.service.workspace.WorkspaceService.get_arbitrary_info_if_use_arbitrary", return_value=None
        )
        resp = await client.post(self.answer_upload_url.format(applet_id=applet_one.id), data={"file_id": file_id})
        assert resp.status_code == http.HTTPStatus.OK
        assert resp.json()["result"]["fields"]["key"] == expected_key
        url = CDNClient(
            CdnConfig(region="region", bucket=bucket_name, secret_key="secret_key", access_key="access_key"), "env"
        ).generate_private_url(expected_key)
        assert resp.json()["result"]["url"] == url

    @pytest.mark.usefixtures("mock_presigned_post")
    async def test_generate_presigned_log_url__logs_are_uploaded_to_the_answer_bucket(
        self, client: TestClient, device_tom: str, tom: User, mocker: MockerFixture
    ):
        bucket_answer_name = "bucket_answer_test"
        settings.cdn.bucket_answer = bucket_answer_name
        config = CdnConfig(
            endpoint_url=settings.cdn.endpoint_url,
            access_key=settings.cdn.access_key,
            secret_key=settings.cdn.secret_key,
            region=settings.cdn.region,
            bucket=settings.cdn.bucket_answer,
            ttl_signed_urls=settings.cdn.ttl_signed_urls,
        )
        cdn_client = CDNClient(config, env="env")
        mocker.patch("infrastructure.dependency.cdn.get_log_bucket", return_value=cdn_client)
        await client.login(self.login_url, "tom@mindlogger.com", "Test1234!")
        file_name = "test.txt"
        resp = await client.post(self.log_upload_url.format(device_id=device_tom), data={"file_id": file_name})
        assert resp.status_code == http.HTTPStatus.OK
        key = resp.json()["result"]["fields"]["key"]
        expected_key = LogFileService(tom.id, cdn_client).key(device_tom, file_name)
        assert key == expected_key
        assert bucket_answer_name in resp.json()["result"]["uploadUrl"]

    @pytest.mark.usefixtures("mock_presigned_post")
    @pytest.mark.parametrize("file_name", ("test.webm", "test.WEBM"))
    async def test_generate_presigned_media_for_webm_file__conveted_in_url__upload_url_has_operations_bucket(
        self, client: TestClient, file_name
    ) -> None:
        await client.login(self.login_url, "tom@mindlogger.com", "Test1234!")

        settings.cdn.bucket_operations = "bucket_operations"
        settings.cdn.bucket = "bucket_media"

        resp = await client.post(self.upload_media_url, data={"file_name": file_name})
        assert resp.status_code == http.HTTPStatus.OK
        result = resp.json()["result"]
        exp_converted_file_name = file_name + ".mp3"
        assert result["fields"]["key"].endswith(file_name)
        assert result["url"].endswith(exp_converted_file_name)
        assert result["fields"]["key"].startswith(settings.cdn.bucket)
        assert settings.cdn.bucket_operations in result["uploadUrl"]

    @pytest.mark.usefixtures("mock_presigned_post")
    @pytest.mark.parametrize("file_name", ("answer.heic", "answer.HEIC"))
    async def test_generate_presigned_for_answer_for_heic_format_not_arbitrary(
        self, client: TestClient, mocker: MockerFixture, applet_one: AppletFull, file_name: str
    ) -> None:
        await client.login(self.login_url, "tom@mindlogger.com", "Test1234!")

        settings.cdn.bucket_operations = "bucket_operations"
        settings.cdn.bucket_answer = "bucket_answer"
        mocker.patch(
            "apps.workspaces.service.workspace.WorkspaceService.get_arbitrary_info_if_use_arbitrary", return_value=None
        )

        resp = await client.post(self.answer_upload_url.format(applet_id=applet_one.id), data={"file_id": file_name})
        assert resp.status_code == http.HTTPStatus.OK
        result = resp.json()["result"]
        exp_converted_file_name = file_name + ".jpg"
        assert result["fields"]["key"].endswith(file_name)
        assert result["fields"]["key"].startswith(settings.cdn.bucket_answer)
        assert result["url"].endswith(exp_converted_file_name)
        assert settings.cdn.bucket_answer in result["url"]
        assert settings.cdn.bucket_operations in result["uploadUrl"]

    @pytest.mark.usefixtures("mock_presigned_post")
    async def test_generate_presigned_for_answer_for_heic_format_arbitrary_workspace(
        self, client: TestClient, applet_one: AppletFull, session: AsyncSession
    ) -> None:
        await client.login(self.login_url, "tom@mindlogger.com", "Test1234!")

        file_name = "answer.heic"
        settings.cdn.bucket_operations = "bucket_operations"
        await set_storage_type(StorageType.AWS, session)
        resp = await client.post(self.answer_upload_url.format(applet_id=applet_one.id), data={"file_id": file_name})
        assert resp.status_code == http.HTTPStatus.OK
        result = resp.json()["result"]
        exp_converted_file_name = file_name + ".jpg"
        assert result["fields"]["key"].endswith(file_name)
        assert result["fields"]["key"].startswith(f"arbitrary-{WORKSPACE_ARBITRARY_ID}")
        assert result["url"].endswith(exp_converted_file_name)
        assert ARBITRARY_BUCKET_NAME in result["url"]
        assert settings.cdn.bucket_operations in result["uploadUrl"]

    @pytest.mark.usefixtures("mock_presigned_post")
    async def test_answer_existance_for_heic_format_not_arbitrary(
        self, client: TestClient, tom: User, applet_one: AppletFull, mocker: MockerFixture
    ) -> None:
        await client.login(self.login_url, "tom@mindlogger.com", "Test1234!")

        file_name = "answer.heic"
        settings.cdn.bucket_operations = "bucket_operations"
        settings.cdn.bucket_answer = "bucket_answer"
        mock_check_existance = mocker.patch("infrastructure.utility.cdn_client.CDNClient.check_existence")
        mocker.patch(
            "apps.workspaces.service.workspace.WorkspaceService.get_arbitrary_info_if_use_arbitrary", return_value=None
        )
        resp = await client.post(
            self.existance_url.format(applet_id=applet_one.id),
            data={"files": [file_name]},
        )
        assert resp.status_code == http.HTTPStatus.OK
        result = resp.json()["result"]
        exp_converted_file_name = file_name + ".jpg"
        check_key = CDNClient.generate_key(FileScopeEnum.ANSWER, f"{tom.id}/{applet_one.id}", file_name)
        exp_check_key = f"{settings.cdn.bucket_answer}/{check_key}"

        mock_check_existance.assert_awaited_once_with(settings.cdn.bucket_operations, exp_check_key)
        assert result[0]["url"].endswith(exp_converted_file_name)
        assert settings.cdn.bucket_answer in result[0]["url"]

    @pytest.mark.usefixtures("mock_presigned_post")
    async def test_answer_existance_for_heic_format_for_arbitrary(
        self, client: TestClient, tom: User, applet_one: AppletFull, session: AsyncSession, mocker: MockerFixture
    ) -> None:
        await client.login(self.login_url, "tom@mindlogger.com", "Test1234!")

        file_name = "answer.heic"
        settings.cdn.bucket_operations = "bucket_operations"
        settings.cdn.bucket_answer = "bucket_answer"
        mock_check_existance = mocker.patch("infrastructure.utility.cdn_arbitrary.ArbitraryS3CdnClient.check_existence")
        await set_storage_type(StorageType.AWS, session)
        resp = await client.post(
            self.existance_url.format(applet_id=applet_one.id),
            data={"files": [file_name]},
        )
        assert resp.status_code == http.HTTPStatus.OK
        result = resp.json()["result"]
        exp_converted_file_name = file_name + ".jpg"
        check_key = CDNClient.generate_key(FileScopeEnum.ANSWER, f"{tom.id}/{applet_one.id}", file_name)
        exp_check_key = f"arbitrary-{WORKSPACE_ARBITRARY_ID}/{check_key}"

        mock_check_existance.assert_awaited_once_with(settings.cdn.bucket_operations, exp_check_key)
        assert result[0]["url"].endswith(exp_converted_file_name)
        assert ARBITRARY_BUCKET_NAME in result[0]["url"]

    @pytest.mark.usefixtures("mock_presigned_post")
    @pytest.mark.parametrize(
        "file_name,target_extension,exp_file_name",
        (
            ("test.webm", WebmTargetExtenstion.MP3, f"test.webm{WebmTargetExtenstion.MP3}"),
            ("test.webm", WebmTargetExtenstion.MP4, f"test.webm{WebmTargetExtenstion.MP4}"),
            ("test.webm", None, f"test.webm{WebmTargetExtenstion.MP3}"),
            ("test.webm", "without extension", f"test.webm{WebmTargetExtenstion.MP3}"),
        ),
    )
    async def test_generate_upload_url__webm_to_mp3_mp4(
        self, client: TestClient, file_name: str, target_extension: WebmTargetExtenstion, exp_file_name: str
    ):
        await client.login(self.login_url, "tom@mindlogger.com", "Test1234!")
        data = {"file_name": file_name, "target_extension": target_extension}
        if target_extension == "without extension":
            del data["target_extension"]
        resp = await client.post(self.upload_media_url, data=data)
        assert resp.status_code == http.HTTPStatus.OK
        result = resp.json()["result"]
        assert result["url"].endswith(exp_file_name)

    @pytest.mark.parametrize("not_valid_extesion", ("mp3", "mp2"))
    async def test_generate_upload_url__webm_to_mp3_mp4_not_valid_extension(
        self, client: TestClient, not_valid_extesion: str
    ):
        await client.login(self.login_url, "tom@mindlogger.com", "Test1234!")
        data = {"file_name": "test.webm", "target_extension": not_valid_extesion}
        resp = await client.post(self.upload_media_url, data=data)
        assert resp.status_code == http.HTTPStatus.UNPROCESSABLE_ENTITY
