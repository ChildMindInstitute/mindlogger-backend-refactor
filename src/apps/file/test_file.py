import http
import io
from typing import Any, Callable, Generator, cast

import pytest
from botocore.exceptions import ClientError, EndpointConnectionError
from pytest import LogCaptureFixture
from pytest_mock import MockerFixture
from sqlalchemy.ext.asyncio import AsyncSession

from apps.applets.domain.applet_full import AppletFull
from apps.file.domain import WebmTargetExtenstion
from apps.file.enums import FileScopeEnum
from apps.file.errors import FileNotFoundError, SomethingWentWrongError
from apps.file.services import LogFileService
from apps.shared.exception import AccessDeniedError, NotFoundError
from apps.shared.test import BaseTest
from apps.shared.test.client import TestClient
from apps.users.domain import User
from apps.workspaces.constants import StorageType
from apps.workspaces.db.schemas import UserWorkspaceSchema
from apps.workspaces.domain.workspace import WorkspaceArbitrary, WorkspaceArbitraryCreate
from apps.workspaces.errors import AnswerViewAccessDenied
from apps.workspaces.service.workspace import WorkspaceService
from config import settings
from config.cdn import CDNSettings
from infrastructure.storage.cdn_arbitrary import ArbitraryS3CdnClient
from infrastructure.storage.cdn_client import CDNClient
from infrastructure.storage.cdn_config import CdnConfig


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

    m = mocker.patch("botocore.signers.generate_presigned_post", new=fake_generate_presigned_post)
    return m


@pytest.fixture
def mock_presigned_url(mocker: MockerFixture) -> Callable[..., str]:
    def fake__generate_presigned_url(_: CDNClient, key: str) -> str:
        return f"{key}?credentials"

    m = mocker.patch(
        "infrastructure.storage.cdn_client.CDNClient._generate_presigned_url", new=fake__generate_presigned_url
    )
    return m


@pytest.fixture
async def tom_workspace_arbitrary_aws(tom: User, arbitrary_db_url: str, session: AsyncSession) -> WorkspaceArbitrary:
    srv = WorkspaceService(session, tom.id)
    await srv.create_workspace_from_user(tom)
    data = WorkspaceArbitraryCreate(
        database_uri=arbitrary_db_url,
        storage_type=StorageType.AWS,
        storage_access_key="storage_access_key",
        storage_secret_key="storage_secret_key",
        storage_region="us-east-1",
        storage_bucket="aws-bucket",
        use_arbitrary=True,
    )
    await srv.set_arbitrary_server(data, rewrite=True)
    ws = await srv.get_arbitrary_info_by_owner_id_if_use_arbitrary(tom.id)
    ws = cast(WorkspaceArbitrary, ws)
    return ws


@pytest.fixture
async def tom_workspace_arbitrary_gcp(tom: User, arbitrary_db_url: str, session: AsyncSession) -> WorkspaceArbitrary:
    srv = WorkspaceService(session, tom.id)
    await srv.create_workspace_from_user(tom)
    data = WorkspaceArbitraryCreate(
        database_uri=arbitrary_db_url,
        storage_type=StorageType.GCP,
        storage_url="storage_url",
        storage_access_key="storage_access_key",
        storage_secret_key="storage_secret_key",
        storage_region="US-CENTRAL1",
        storage_bucket="gcp-bucket",
        use_arbitrary=True,
    )
    await srv.set_arbitrary_server(data, rewrite=True)
    ws = await srv.get_arbitrary_info_by_owner_id_if_use_arbitrary(tom.id)
    ws = cast(WorkspaceArbitrary, ws)
    return ws


@pytest.fixture
async def tom_workspace_arbitrary_azure(tom: User, arbitrary_db_url: str, session: AsyncSession) -> WorkspaceArbitrary:
    srv = WorkspaceService(session, tom.id)
    await srv.create_workspace_from_user(tom)
    data = WorkspaceArbitraryCreate(
        database_uri=arbitrary_db_url,
        storage_type=StorageType.AZURE,
        storage_url="storage_url",
        storage_access_key="storage_access_key",
        storage_secret_key="storage_secret_key",
        storage_region="westcentralus",
        storage_bucket="azure-bucket",
        use_arbitrary=True,
    )
    await srv.set_arbitrary_server(data, rewrite=True)
    ws = await srv.get_arbitrary_info_by_owner_id_if_use_arbitrary(tom.id)
    ws = cast(WorkspaceArbitrary, ws)
    return ws


@pytest.fixture(scope="class")
def cdn_settings() -> Generator[CDNSettings, Any, None]:
    settings.cdn.access_key = "access_key"
    settings.cdn.secret_key = "secret_key"
    settings.cdn.bucket = "bucket"
    settings.cdn.bucket_answer = "bucket_answer"
    settings.cdn.bucket_operations = "bucket_operations"
    settings.cdn.region = "us-east-1"
    settings.cdn.domain = "mindlogger"
    settings.cdn.legacy_prefix = "mindlogger/legacy-answer"
    yield settings.cdn
    settings.cdn.bucket_operations = None
    settings.cdn.access_key = None
    settings.cdn.secret_key = None
    settings.cdn.bucket = None
    settings.cdn.bucket_answer = None
    settings.cdn.region = None
    settings.cdn.domain = ""
    settings.cdn.legacy_prefix = None


@pytest.fixture(scope="class")
def cdn_client(cdn_settings: CDNSettings) -> CDNClient:
    config = CdnConfig(
        endpoint_url=cdn_settings.endpoint_url,
        access_key=cdn_settings.access_key,
        secret_key=cdn_settings.secret_key,
        region=cdn_settings.region,
        bucket=cdn_settings.bucket_answer,
        ttl_signed_urls=cdn_settings.ttl_signed_urls,
    )
    cdn_client = CDNClient(config, env="env")
    return cdn_client


@pytest.fixture
def cdn_client_arbitrary_aws(tom_workspace_arbitrary_aws: WorkspaceArbitrary) -> ArbitraryS3CdnClient:
    client = ArbitraryS3CdnClient(
        CdnConfig(
            region=tom_workspace_arbitrary_aws.storage_region,
            bucket=tom_workspace_arbitrary_aws.storage_bucket,
            secret_key=tom_workspace_arbitrary_aws.storage_secret_key,
            access_key=tom_workspace_arbitrary_aws.storage_access_key,
        ),
        "env",
    )
    return client


@pytest.fixture
def log_file_service(tom: User, cdn_client: CDNClient) -> LogFileService:
    return LogFileService(tom.id, cdn_client)


@pytest.mark.usefixtures("cdn_settings")
class TestAnswerActivityItems(BaseTest):
    login_url = "/auth/login"
    upload_url = "file/{applet_id}/upload"
    download_url = "/file/download"
    answer_download_url = "file/{applet_id}/download"
    existance_url = "/file/{applet_id}/upload/check"
    file_id = "1693560380000/c60859c4-6f5f-4390-a572-da85fcd59709"
    upload_media_url = "/file/upload-url"
    answer_upload_url = "/file/{applet_id}/upload-url"
    log_upload_url = "/file/log-file/{device_id}/upload-url"
    presign_url = "/file/{applet_id}/presign"
    log_upload_old_url = "/file/log-file/{device_id}"
    log_download_url = "/file/log-file/{user_email}/{device_id}"
    log_check_url = "/file/log-file/{device_id}/check"


    @pytest.mark.usefixtures("tom_workspace_arbitrary_aws")
    async def test_arbitrary_upload_to_s3_aws(
        self, client: TestClient, applet_one: AppletFull, tom: User, mocker: MockerFixture
    ):
        client.login(tom)

        content = io.BytesIO(b"File content")
        mock = mocker.patch("infrastructure.storage.cdn_arbitrary.ArbitraryS3CdnClient.upload")
        response = await client.post(
            self.upload_url.format(applet_id=applet_one.id),
            query={"fileId": self.file_id},
            files={"file": content},
        )
        assert http.HTTPStatus.OK == response.status_code
        mock.assert_awaited_once()

    @pytest.mark.usefixtures("tom_workspace_arbitrary_aws")
    async def test_arbitrary_download_from_s3_aws(
        self, client: TestClient, applet_one: AppletFull, tom: User, mocker: MockerFixture
    ):
        client.login(tom)
        mock = mocker.patch(
            "infrastructure.storage.cdn_arbitrary.ArbitraryS3CdnClient.download",
            return_value=(iter(("a", "b")), "txt"),
        )
        response = await client.post(
            self.answer_download_url.format(applet_id=applet_one.id),
            data={"key": "key"},
        )
        assert http.HTTPStatus.OK == response.status_code
        mock.assert_called_once()

    @pytest.mark.usefixtures("tom_workspace_arbitrary_gcp")
    async def test_arbitrary_upload_to_s3_gcp(
        self, client: TestClient, applet_one: AppletFull, tom: User, mocker: MockerFixture
    ):
        client.login(tom)
        mock = mocker.patch("infrastructure.storage.cdn_arbitrary.ArbitraryGCPCdnClient.upload")
        content = io.BytesIO(b"File content")
        response = await client.post(
            self.upload_url.format(applet_id=applet_one.id),
            query={"file_id": self.file_id},
            files={"file": content},
        )
        assert http.HTTPStatus.OK == response.status_code
        mock.assert_awaited_once()

    @pytest.mark.usefixtures("tom_workspace_arbitrary_gcp")
    async def test_arbitrary_download_from_s3_gcp(
        self, client: TestClient, applet_one: AppletFull, tom: User, mocker: MockerFixture
    ):
        client.login(tom)
        mock = mocker.patch(
            "infrastructure.storage.cdn_arbitrary.ArbitraryGCPCdnClient.download",
            return_value=(iter(("a", "b")), "txt"),
        )
        response = await client.post(
            self.answer_download_url.format(applet_id=applet_one.id),
            data={"key": "key"},
        )
        assert http.HTTPStatus.OK == response.status_code
        mock.assert_called_once()

    @pytest.mark.usefixtures("tom_workspace_arbitrary_azure")
    async def test_arbitrary_upload_to_blob_azure(
        self, client: TestClient, applet_one: AppletFull, tom: User, mocker: MockerFixture
    ):
        client.login(tom)
        mocker.patch("infrastructure.storage.cdn_arbitrary.ArbitraryAzureCdnClient._configure_client")
        mock = mocker.patch("infrastructure.storage.cdn_arbitrary.ArbitraryAzureCdnClient.upload")
        content = io.BytesIO(b"File content")
        response = await client.post(
            self.upload_url.format(applet_id=applet_one.id),
            query={"file_id": self.file_id},
            files={"file": content},
        )
        assert http.HTTPStatus.OK == response.status_code
        mock.assert_awaited_once()

    async def test_default_storage_check_existence(
        self, client: TestClient, applet_one: AppletFull, tom: User, mocker: MockerFixture
    ):
        client.login(tom)
        mock = mocker.patch("infrastructure.storage.cdn_arbitrary.CDNClient.check_existence")
        response = await client.post(
            self.existance_url.format(applet_id=applet_one.id),
            data={"files": [self.file_id]},
        )
        assert http.HTTPStatus.OK == response.status_code
        mock.assert_awaited_once()

    @pytest.mark.usefixtures("tom_workspace_arbitrary_aws")
    async def test_arbitary_s3_aws_check_existence(
        self, client: TestClient, applet_one: AppletFull, tom: User, mocker: MockerFixture
    ):
        client.login(tom)
        mock = mocker.patch("infrastructure.storage.cdn_arbitrary.ArbitraryS3CdnClient.check_existence")
        response = await client.post(
            self.existance_url.format(applet_id=applet_one.id),
            data={"files": [self.file_id]},
        )
        assert http.HTTPStatus.OK == response.status_code
        mock.assert_awaited_once()

    @pytest.mark.usefixtures("mock_presigned_post")
    @pytest.mark.parametrize("file_name,", ("test1.jpg", "test2.jpg"))
    async def test_generate_upload_url(self, client: TestClient, file_name: str, tom: User, cdn_settings: CDNSettings):
        client.login(tom)
        resp = await client.post(self.upload_media_url, data={"file_name": file_name})
        assert resp.status_code == http.HTTPStatus.OK
        result = resp.json()["result"]
        assert result["fields"]["key"].endswith(file_name)
        assert result["url"] == cdn_settings.url.format(key=result["fields"]["key"])

    async def test_generate_presigned_url_for_post_answer__user_does_not_have_access_to_the_applet(
        self, client: TestClient, user: User, applet_one: AppletFull
    ):
        client.login(user)
        resp = await client.post(self.answer_upload_url.format(applet_id=applet_one.id), data={"file_id": "test.txt"})
        assert resp.status_code == http.HTTPStatus.FORBIDDEN
        result = resp.json()["result"]
        assert len(result) == 1
        assert result[0]["message"] == AnswerViewAccessDenied.message

    @pytest.mark.usefixtures("mock_presigned_post")
    async def test_generate_presigned_url_for_answers(
        self, client: TestClient, tom: User, applet_one: AppletFull, cdn_client: CDNClient
    ):
        client.login(tom)
        expected_key = cdn_client.generate_key(
            FileScopeEnum.ANSWER, f"{tom.id}/{applet_one.id}", self.file_id
        )
        resp = await client.post(self.answer_upload_url.format(applet_id=applet_one.id), data={"file_id": self.file_id})
        assert resp.status_code == http.HTTPStatus.OK
        assert resp.json()["result"]["fields"]["key"] == expected_key
        assert resp.json()["result"]["url"] == cdn_client.generate_private_url(expected_key)

    @pytest.mark.usefixtures("mock_presigned_post")
    async def test_generate_presigned_url_for_answers_arbitrary(
        self, client: TestClient, tom: User, applet_one: AppletFull, cdn_client_arbitrary_aws: ArbitraryS3CdnClient
    ):
        client.login(tom)
        expected_key = cdn_client_arbitrary_aws.generate_key(
            FileScopeEnum.ANSWER, f"{tom.id}/{applet_one.id}", self.file_id
        )
        resp = await client.post(self.answer_upload_url.format(applet_id=applet_one.id), data={"file_id": self.file_id})
        assert resp.status_code == http.HTTPStatus.OK
        assert resp.json()["result"]["fields"]["key"] == expected_key
        assert resp.json()["result"]["url"] == cdn_client_arbitrary_aws.generate_private_url(expected_key)


    @pytest.mark.usefixtures("mock_presigned_post")
    async def test_generate_presigned_log_url__logs_are_uploaded_to_the_answer_bucket(
        self,
        client: TestClient,
        device_tom: str,
        tom: User,
        mocker: MockerFixture,
        cdn_client: CDNClient,
        cdn_settings: CDNSettings,
    ):
        mocker.patch("infrastructure.storage.buckets.get_log_bucket", return_value=cdn_client)
        client.login(tom)
        file_name = "test.txt"
        resp = await client.post(self.log_upload_url.format(device_id=device_tom), data={"file_id": file_name})
        assert resp.status_code == http.HTTPStatus.OK
        key = resp.json()["result"]["fields"]["key"]
        expected_key = LogFileService(tom.id, cdn_client).key(device_tom, file_name)
        assert key == expected_key
        assert cdn_settings.bucket_answer in resp.json()["result"]["uploadUrl"]

    @pytest.mark.usefixtures("mock_presigned_post")
    @pytest.mark.parametrize("file_name", ("test.webm", "test.WEBM"))
    async def test_generate_presigned_media_for_webm_file__conveted_in_url__upload_url_has_operations_bucket(
        self, client: TestClient, file_name, tom: User, cdn_settings: CDNSettings
    ) -> None:
        client.login(tom)

        resp = await client.post(self.upload_media_url, data={"file_name": file_name})
        assert resp.status_code == http.HTTPStatus.OK
        result = resp.json()["result"]
        exp_converted_file_name = file_name + ".mp3"
        assert result["fields"]["key"].endswith(file_name)
        assert result["url"].endswith(exp_converted_file_name)
        assert result["fields"]["key"].startswith(cdn_settings.bucket)
        assert cdn_settings.bucket_operations in result["uploadUrl"]

    # @pytest.mark.usefixtures("mock_presigned_post")
    # @pytest.mark.parametrize("file_name", ("answer.heic", "answer.HEIC"))
    # async def test_generate_presigned_for_answer_for_heic_format_not_arbitrary(
    #     self, client: TestClient, applet_one: AppletFull, file_name: str, tom: User, cdn_settings: CDNSettings
    # ) -> None:
    #     client.login(tom)
    #     resp = await client.post(self.answer_upload_url.format(applet_id=applet_one.id), data={"file_id": file_name})
    #     assert resp.status_code == http.HTTPStatus.OK
    #     result = resp.json()["result"]
    #     exp_converted_file_name = file_name + ".jpg"
    #     assert result["fields"]["key"].endswith(file_name)
    #     assert result["fields"]["key"].startswith(cdn_settings.bucket_answer)
    #     assert result["url"].endswith(exp_converted_file_name)
    #     assert cdn_settings.bucket_answer in result["url"]
    #     assert cdn_settings.bucket_operations in result["uploadUrl"]

    # @pytest.mark.usefixtures("mock_presigned_post")
    # async def test_generate_presigned_for_answer_for_heic_format_arbitrary_workspace(
    #     self,
    #     client: TestClient,
    #     applet_one: AppletFull,
    #     tom: User,
    #     tom_workspace_arbitrary_aws: UserWorkspaceSchema,
    #     cdn_settings: CDNSettings,
    # ) -> None:
    #     client.login(tom)
    #
    #     file_name = "answer.heic"
    #     resp = await client.post(self.answer_upload_url.format(applet_id=applet_one.id), data={"file_id": file_name})
    #     assert resp.status_code == http.HTTPStatus.OK
    #     result = resp.json()["result"]
    #     exp_converted_file_name = file_name + ".jpg"
    #     assert result["fields"]["key"].endswith(file_name)
    #     assert result["fields"]["key"].startswith(f"arbitrary-{tom_workspace_arbitrary_aws.id}")
    #     assert result["url"].endswith(exp_converted_file_name)
    #     assert str(tom.id) in result["url"]
    #     assert cdn_settings.bucket_operations in result["uploadUrl"]
    #
    # @pytest.mark.usefixtures("mock_presigned_post")
    # async def test_answer_existance_for_heic_format_not_arbitrary(
    #     self,
    #     client: TestClient,
    #     tom: User,
    #     applet_one: AppletFull,
    #     mocker: MockerFixture,
    #     cdn_settings: CDNSettings,
    # ) -> None:
    #     client.login(tom)
    #
    #     file_name = "answer.heic"
    #     mock_check_existance = mocker.patch("infrastructure.storage.cdn_client.CDNClient.check_existence")
    #     resp = await client.post(
    #         self.existance_url.format(applet_id=applet_one.id),
    #         data={"files": [file_name]},
    #     )
    #     assert resp.status_code == http.HTTPStatus.OK
    #     result = resp.json()["result"]
    #     exp_converted_file_name = file_name + ".jpg"
    #     check_key = CDNClient.generate_key(FileScopeEnum.ANSWER, f"{tom.id}/{applet_one.id}", file_name)
    #     exp_check_key = f"{cdn_settings.bucket_answer}/{check_key}"
    #
    #     mock_check_existance.assert_awaited_once_with(cdn_settings.bucket_operations, exp_check_key)
    #     assert result[0]["url"].endswith(exp_converted_file_name)
    #     assert cdn_settings.bucket_answer in result[0]["url"]
    #
    # @pytest.mark.usefixtures("mock_presigned_post")
    # async def test_answer_existance_for_heic_format_for_arbitrary(
    #     self,
    #     client: TestClient,
    #     tom: User,
    #     applet_one: AppletFull,
    #     mocker: MockerFixture,
    #     tom_workspace_arbitrary_aws: UserWorkspaceSchema,
    #     cdn_settings: CDNSettings,
    # ) -> None:
    #     client.login(tom)
    #
    #     file_name = "answer.heic"
    #     mock_check_existance = mocker.patch("infrastructure.storage.cdn_arbitrary.ArbitraryS3CdnClient.check_existence")
    #     resp = await client.post(
    #         self.existance_url.format(applet_id=applet_one.id),
    #         data={"files": [file_name]},
    #     )
    #     assert resp.status_code == http.HTTPStatus.OK
    #     result = resp.json()["result"]
    #     exp_converted_file_name = file_name + ".jpg"
    #     check_key = CDNClient.generate_key(FileScopeEnum.ANSWER, f"{tom.id}/{applet_one.id}", file_name)
    #     exp_check_key = f"arbitrary-{tom_workspace_arbitrary_aws.id}/{check_key}"
    #
    #     mock_check_existance.assert_awaited_once_with(cdn_settings.bucket_operations, exp_check_key)
    #     assert result[0]["url"].endswith(exp_converted_file_name)
    #     assert str(tom.id) in result[0]["url"]

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
        self, client: TestClient, file_name: str, target_extension: WebmTargetExtenstion, exp_file_name: str, tom: User
    ):
        client.login(tom)
        data = {"file_name": file_name, "target_extension": target_extension}
        if target_extension == "without extension":
            del data["target_extension"]
        resp = await client.post(self.upload_media_url, data=data)
        assert resp.status_code == http.HTTPStatus.OK
        result = resp.json()["result"]
        assert result["url"].endswith(exp_file_name)

    @pytest.mark.parametrize("not_valid_extesion", ("mp3", "mp2"))
    async def test_generate_upload_url__webm_to_mp3_mp4_not_valid_extension(
        self, client: TestClient, not_valid_extesion: str, tom: User
    ):
        client.login(tom)
        data = {"file_name": "test.webm", "target_extension": not_valid_extesion}
        resp = await client.post(self.upload_media_url, data=data)
        assert resp.status_code == http.HTTPStatus.UNPROCESSABLE_ENTITY

    async def test_answer_download__answer_is_log(self, client: TestClient, tom: User, applet_one: AppletFull):
        client.login(tom)
        key = LogFileService.LOG_KEY
        resp = await client.post(self.answer_download_url.format(applet_id=applet_one.id), data={"key": key})
        assert resp.status_code == http.HTTPStatus.FORBIDDEN
        result = resp.json()["result"]
        assert len(result) == 1
        assert result[0]["message"] == AccessDeniedError.message

    async def test_answer_download_client_error__file_not_found(
        self, client: TestClient, tom: User, applet_one: AppletFull, mocker: MockerFixture, caplog: LogCaptureFixture
    ):
        client.login(tom)
        data = {"key": self.file_id}
        mocker.patch(
            "botocore.client.BaseClient._make_api_call",
            side_effect=ClientError({"Error": {"Code": "404"}}, "Not Found"),
        )
        resp = await client.post(self.answer_download_url.format(applet_id=applet_one.id), data=data)
        assert resp.status_code == http.HTTPStatus.NOT_FOUND
        result = resp.json()["result"]
        assert len(result) == 1
        assert result[0]["message"] == FileNotFoundError.message
        # assert len(caplog.messages) == 1
        # assert caplog.messages[0] == f"Trying to download not existing file {self.file_id}"

    async def test_answer_download_client_error__unknown_error(
        self, client: TestClient, tom: User, applet_one: AppletFull, mocker: MockerFixture, caplog: LogCaptureFixture
    ):
        client.login(tom)
        data = {"key": self.file_id}
        mocker.patch(
            "botocore.client.BaseClient._make_api_call",
            side_effect=ClientError({"Error": {"Code": "0"}}, "Unknown"),
        )
        resp = await client.post(self.answer_download_url.format(applet_id=applet_one.id), data=data)
        assert resp.status_code == http.HTTPStatus.BAD_REQUEST
        result = resp.json()["result"]
        assert len(result) == 1
        assert result[0]["message"] == SomethingWentWrongError.message
        # assert len(caplog.messages) == 1
        # assert (
        #     caplog.messages[0]
        #     == f"Error when trying to download file {self.file_id}: An error occurred (0) when calling the Unknown operation: Unknown"  # noqa: E501
        # )

    async def test_answer_download_client_error__cdn_client_object_not_found_error(
        self, client: TestClient, tom: User, applet_one: AppletFull, mocker: MockerFixture
    ):
        client.login(tom)
        data = {"key": "key"}
        mocker.patch(
            "botocore.client.BaseClient._make_api_call",
            side_effect=EndpointConnectionError(endpoint_url="not-valid-endpoint"),
        )
        resp = await client.post(self.answer_download_url.format(applet_id=applet_one.id), data=data)
        assert resp.status_code == http.HTTPStatus.NOT_FOUND
        result = resp.json()["result"]
        assert len(result) == 1
        assert result[0]["message"] == FileNotFoundError.message

    async def test_answer_download_client_error__cdn_client_file_not_found_error(
        self, client: TestClient, tom: User, applet_one: AppletFull, mocker: MockerFixture
    ):
        client.login(tom)
        data = {"key": "key"}
        mocker.patch(
            "infrastructure.storage.cdn_client.CDNClient.download",
            side_effect=FileNotFoundError,
        )
        resp = await client.post(self.answer_download_url.format(applet_id=applet_one.id), data=data)
        assert resp.status_code == http.HTTPStatus.NOT_FOUND
        result = resp.json()["result"]
        assert len(result) == 1
        assert result[0]["message"] == FileNotFoundError.message

    async def test_general_file_download_client_error__file_not_found(
        self, client: TestClient, tom: User, mocker: MockerFixture, caplog: LogCaptureFixture
    ):
        client.login(tom)
        data = {"key": self.file_id}
        mocker.patch(
            "botocore.client.BaseClient._make_api_call",
            side_effect=ClientError({"Error": {"Code": "404"}}, "Not Found"),
        )
        resp = await client.post(self.download_url, data=data)
        assert resp.status_code == http.HTTPStatus.NOT_FOUND
        result = resp.json()["result"]
        assert len(result) == 1
        assert result[0]["message"] == FileNotFoundError.message
        # assert len(caplog.messages) == 1
        # assert caplog.messages[0] == f"Trying to download not existing file {self.file_id}"

    async def test_general_file_download_client_error__unknown_error(
        self, client: TestClient, tom: User, mocker: MockerFixture, caplog: LogCaptureFixture
    ):
        client.login(tom)
        data = {"key": self.file_id}
        mocker.patch(
            "botocore.client.BaseClient._make_api_call",
            side_effect=ClientError({"Error": {"Code": "0"}}, "Unknown"),
        )
        resp = await client.post(self.download_url, data=data)
        assert resp.status_code == http.HTTPStatus.BAD_REQUEST
        result = resp.json()["result"]
        assert len(result) == 1
        assert result[0]["message"] == SomethingWentWrongError.message
        # assert len(caplog.messages) == 1
        # assert (
        #     caplog.messages[0]
        #     == f"Error when trying to download file {self.file_id}: An error occurred (0) when calling the Unknown operation: Unknown"  # noqa: E501
        # )

    async def test_general_file_download_client_error__cdn_client_object_not_found_error(
        self, client: TestClient, tom: User, mocker: MockerFixture
    ):
        client.login(tom)
        data = {"key": "key"}
        mocker.patch(
            "botocore.client.BaseClient._make_api_call",
            side_effect=EndpointConnectionError(endpoint_url="not-valid-endpoint"),
        )
        resp = await client.post(self.download_url, data=data)
        assert resp.status_code == http.HTTPStatus.NOT_FOUND

    async def test_general_file_download_client_error__cdn_client_file_not_found_error(
        self, client: TestClient, tom: User, mocker: MockerFixture
    ):
        client.login(tom)
        data = {"key": "key"}
        mocker.patch(
            "infrastructure.storage.cdn_client.CDNClient.download",
            side_effect=FileNotFoundError,
        )
        resp = await client.post(self.download_url, data=data)
        assert resp.status_code == http.HTTPStatus.NOT_FOUND
        result = resp.json()["result"]
        assert len(result) == 1
        assert result[0]["message"] == FileNotFoundError.message

    async def test_general_file_download(self, client: TestClient, tom: User, mocker: MockerFixture):
        client.login(tom)
        data = {"key": "key"}
        mocker.patch(
            "infrastructure.storage.cdn_client.CDNClient.download",
            return_value=(iter(("a", "b")), "txt"),
        )
        resp = await client.post(self.download_url, data=data)
        assert resp.status_code == http.HTTPStatus.OK
        assert resp.content == b"ab"

    # NOTE: We must keep old answer upload process untill all Mindlogger users have last App version.
    async def test_answer_upload__not_valid_user_role(
        self, client: TestClient, applet_one_lucy_coordinator: AppletFull, lucy: User, mocker: MockerFixture
    ):
        client.login(lucy)

        content = io.BytesIO(b"File content")
        mocker.patch("infrastructure.storage.cdn_client.CDNClient.upload")
        resp = await client.post(
            self.upload_url.format(applet_id=applet_one_lucy_coordinator.id),
            query={"file_id": self.file_id},
            files={"file": content},
        )
        assert resp.status_code == http.HTTPStatus.FORBIDDEN
        result = resp.json()["result"]
        assert len(result) == 1
        assert result[0]["message"] == AnswerViewAccessDenied.message

    async def test_check_answer_file_uploaded__not_valid_user_role(
        self, client: TestClient, applet_one_lucy_coordinator: AppletFull, lucy: User
    ):
        client.login(lucy)
        resp = await client.post(
            self.existance_url.format(applet_id=applet_one_lucy_coordinator.id),
            data={"files": [self.file_id]},
        )
        assert resp.status_code == http.HTTPStatus.FORBIDDEN
        result = resp.json()["result"]
        assert len(result) == 1
        assert result[0]["message"] == AnswerViewAccessDenied.message

    async def test_check_answer_file_uploaded__file_does_not_exist(
        self, client: TestClient, applet_one: AppletFull, tom: User, mocker: MockerFixture
    ):
        client.login(tom)
        mocker.patch("infrastructure.storage.cdn_client.CDNClient._check_existence", side_effect=NotFoundError)
        resp = await client.post(
            self.existance_url.format(applet_id=applet_one.id),
            data={"files": [self.file_id]},
        )
        assert resp.status_code == http.HTTPStatus.OK
        result = resp.json()["result"]
        assert len(result) == 1
        assert not result[0]["uploaded"]
        assert result[0]["url"] is None
        assert resp.json()["count"] == 1

    @pytest.mark.usefixtures("mock_presigned_url")
    async def test_presign_answer_url(self, client: TestClient, applet_one: AppletFull, tom: User):
        client.login(tom)
        key = self.file_id
        private_url = f"s3://bucket/mindlogger/answer/{tom.id}/{applet_one.id}/{key}"
        resp = await client.post(self.presign_url.format(applet_id=applet_one.id), data={"privateUrls": [private_url]})
        assert resp.status_code == http.HTTPStatus.OK
        result = resp.json()["result"]
        assert len(result) == 1
        assert result[0].endswith(key + "?credentials")
        assert resp.json()["count"] == 1

    @pytest.mark.usefixtures("mock_presigned_url")
    async def test_presign_legacy_answer_url(self, client: TestClient, applet_legacy: AppletFull, kate: User):
        client.login(kate)
        key = self.file_id

        # applet id to mongo id
        mongo_applet_id = str(applet_legacy.id).replace("00000000", "").replace("-", "")

        private_url = f"s3://legacy-bucket/64f9a0b322d818224fd399df/64cbb57922d8180cf9b3eab7/{mongo_applet_id}/{key}"
        resp = await client.post(self.presign_url.format(applet_id=applet_legacy.id), data={"privateUrls": [private_url]})
        assert resp.status_code == http.HTTPStatus.OK
        result = resp.json()["result"]
        assert len(result) == 1
        assert result[0].endswith(key + "?credentials")
        assert resp.json()["count"] == 1

    @pytest.mark.usefixtures("mock_presigned_url")
    async def test_presign_legacy_answer_url_no_access(self, client: TestClient, applet_legacy: AppletFull, tom: User):
        client.login(tom)
        key = self.file_id

        # applet id to mongo id
        mongo_applet_id = str(applet_legacy.id).replace("00000000", "").replace("-", "")

        private_url = f"s3://legacy-bucket/64f9a0b322d818224fd399df/64cbb57922d8180cf9b3eab7/{mongo_applet_id}/{key}"
        resp = await client.post(
            self.presign_url.format(applet_id=applet_legacy.id), data={"privateUrls": [private_url]}
        )
        assert resp.status_code == http.HTTPStatus.FORBIDDEN
        result = resp.json()["result"]
        assert len(result) == 1
        assert result[0]["message"] == AnswerViewAccessDenied.message

    async def test_upload_logs(
        self, client: TestClient, device_tom: str, mocker: MockerFixture, tom: User, cdn_settings: CDNSettings
    ):
        client.login(tom)
        mocker.patch("apps.file.services.LogFileService.upload")
        content = io.BytesIO(b"File content")
        file_id = "file_id"
        resp = await client.post(
            self.log_upload_old_url.format(device_id=device_tom),
            files={"file": content},
            query={"fileId": file_id},
        )
        assert resp.status_code == http.HTTPStatus.OK
        result = resp.json()["result"]
        assert str(tom.id) in result["key"]
        assert device_tom in result["key"]
        assert str(tom.id) in result["url"]
        assert cdn_settings.bucket_answer in result["url"]
        assert cdn_settings.access_key in result["url"]
        assert file_id == result["fileId"]

    async def test_upload_logs__error_during_upload(
        self, client: TestClient, device_tom: str, mocker: MockerFixture, tom: User, caplog: LogCaptureFixture
    ):
        client.login(tom)
        mocker.patch(
            "botocore.client.BaseClient._make_api_call",
            side_effect=ClientError({"Error": {"Code": "0"}}, "Unknown"),
        )
        content = io.BytesIO(b"File content")
        file_id = "file_id"
        resp = await client.post(
            self.log_upload_old_url.format(device_id=device_tom),
            files={"file": content},
            query={"fileId": file_id},
        )
        assert resp.status_code == http.HTTPStatus.BAD_REQUEST
        result = resp.json()["result"]
        assert len(result) == 1
        assert result[0]["message"] == SomethingWentWrongError.message
        # assert len(caplog.messages) == 1

    async def test_upload_logs__arbitrary_logs_are_uploaded_to_the_mindlogger_answer_bucket(
        self,
        client: TestClient,
        device_tom: str,
        mocker: MockerFixture,
        tom: User,
        cdn_settings: CDNSettings,
        tom_workspace_arbitrary_aws: WorkspaceArbitrary,
    ):
        client.login(tom)
        mocker.patch("apps.file.services.LogFileService.upload")
        content = io.BytesIO(b"File content")
        file_id = "file_id"
        resp = await client.post(
            self.log_upload_old_url.format(device_id=device_tom),
            files={"file": content},
            query={"fileId": file_id},
        )
        assert resp.status_code == http.HTTPStatus.OK
        result = resp.json()["result"]
        assert cdn_settings.bucket_answer in result["url"]
        assert tom_workspace_arbitrary_aws.storage_bucket not in result["url"]

    async def test_download_logs__days_in_query_parameters_are_required(
        self, client: TestClient, device_tom: str, tom: User
    ):
        client.login(tom)
        resp = await client.get(
            self.log_download_url.format(device_id=device_tom, user_email=tom.email_encrypted),
        )
        assert resp.status_code == http.HTTPStatus.UNPROCESSABLE_ENTITY
        result = resp.json()["result"]
        assert len(result) == 1
        assert result[0]["message"] == "field required"
        assert result[0]["path"] == ["query", "days"]

    async def test_download_logs__user_is_not_developer(self, client: TestClient, device_tom: str, tom: User):
        client.login(tom)
        resp = await client.get(
            self.log_download_url.format(device_id=device_tom, user_email=tom.email_encrypted),
            query={"days": 1},
        )
        assert resp.status_code == http.HTTPStatus.FORBIDDEN
        result = resp.json()["result"]
        assert len(result) == 1
        assert result[0]["message"] == AccessDeniedError.message

    async def test_download_logs__no_logs_for_user(
        self, client: TestClient, device_tom: str, tom: User, mocker: MockerFixture
    ):
        client.login(tom)
        tom.email_encrypted = cast(str, tom.email_encrypted)
        settings.logs.access = tom.email_encrypted
        mocker.patch("apps.file.services.LogFileService.log_list", return_value=[])
        resp = await client.get(
            self.log_download_url.format(device_id=device_tom, user_email=tom.email_encrypted),
            query={"days": 1},
        )
        assert resp.status_code == http.HTTPStatus.OK
        assert not resp.json()["result"]
        assert resp.json()["count"] == 0

    async def test_download_logs(self, client: TestClient, device_tom: str, tom: User, mocker: MockerFixture):
        client.login(tom)
        tom.email_encrypted = cast(str, tom.email_encrypted)
        settings.logs.access = tom.email_encrypted
        mocker.patch("apps.file.services.LogFileService.log_list", return_value=[{"Key": "private-url"}])
        resp = await client.get(
            self.log_download_url.format(device_id=device_tom, user_email=tom.email_encrypted),
            query={"days": 1},
        )
        assert resp.status_code == http.HTTPStatus.OK
        assert resp.json()["result"]
        assert resp.json()["count"] == 1

    async def test_download_logs__unknown_error(
        self, client: TestClient, device_tom: str, tom: User, mocker: MockerFixture, caplog: LogCaptureFixture
    ):
        client.login(tom)
        tom.email_encrypted = cast(str, tom.email_encrypted)
        settings.logs.access = tom.email_encrypted
        mocker.patch(
            "apps.file.services.LogFileService.log_list",
            side_effect=ClientError({"Error": {"Code": "Unknown"}}, "Unknown"),
        )
        resp = await client.get(
            self.log_download_url.format(device_id=device_tom, user_email=tom.email_encrypted),
            query={"days": 1},
        )
        assert resp.status_code == http.HTTPStatus.BAD_REQUEST
        result = resp.json()["result"]
        assert len(result) == 1
        assert result[0]["message"] == SomethingWentWrongError.message
        # assert len(caplog.messages) == 1

    async def test_check_log_exists__no_logs(
        self, client: TestClient, device_tom: str, tom: User, mocker: MockerFixture
    ):
        client.login(tom)
        file_id = "log-file"
        mocker.patch("infrastructure.storage.cdn_client.CDNClient.list_object", return_value=[])
        resp = await client.post(self.log_check_url.format(device_id=device_tom), data={"files": [file_id]})
        assert resp.status_code == http.HTTPStatus.OK
        assert resp.json()["count"] == 1
        result = resp.json()["result"][0]
        assert not result["uploaded"]
        assert result["url"] is None
        assert result["fileId"] == file_id
        assert result["fileSize"] is None

    async def test_check_log_exists(
        self,
        client: TestClient,
        device_tom: str,
        tom: User,
        mocker: MockerFixture,
        log_file_service: LogFileService,
        cdn_settings: CDNSettings,
    ):
        client.login(tom)
        file_id = "log-file"
        s3_key = log_file_service.device_key_prefix(device_tom) + f"/{file_id}"
        mocker.patch("infrastructure.storage.cdn_client.CDNClient.list_object", return_value=[{"Key": s3_key}])
        resp = await client.post(self.log_check_url.format(device_id=device_tom), data={"files": [file_id]})
        assert resp.status_code == http.HTTPStatus.OK
        assert resp.json()["count"] == 1
        result = resp.json()["result"][0]
        assert result["uploaded"]
        assert cdn_settings.access_key in result["url"]
        assert cdn_settings.bucket_answer in result["url"]
        assert s3_key in result["url"]
        assert result["fileId"] == file_id
        assert result["fileSize"] is None
        assert result["key"] == s3_key

    async def test_check_log_exists__unknown_error(
        self, client: TestClient, device_tom: str, tom: User, mocker: MockerFixture, caplog: LogCaptureFixture
    ):
        client.login(tom)
        file_id = "log-file"
        mocker.patch(
            "botocore.client.BaseClient._make_api_call",
            side_effect=ClientError({"Error": {"Code": "0"}}, "Unknown"),
        )
        resp = await client.post(self.log_check_url.format(device_id=device_tom), data={"files": [file_id]})
        assert resp.status_code == http.HTTPStatus.BAD_REQUEST
        result = resp.json()["result"]
        assert len(result) == 1
        assert result[0]["message"] == SomethingWentWrongError.message
        # assert len(caplog.messages) == 1
