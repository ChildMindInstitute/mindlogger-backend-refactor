import http

import pytest
from fastapi import FastAPI

from apps.applets.domain.applet_full import AppletFull
from apps.file.enums import FileScopeEnum
from apps.file.tests import FILE_KEY
from apps.shared.test import BaseTest
from apps.shared.test.client import TestClient
from apps.users import User
from config import Settings, get_settings
from infrastructure.storage.storage import get_media_storage
from infrastructure.storage.storage_client import StorageClient
from infrastructure.storage.storage_config import StorageConfig


class TestAnswerActivityItemsDR(BaseTest):
    # TODO Make these common somewhere
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

    @pytest.fixture
    def override_app_with_dr_settings(self, app: FastAPI, cdn_override_settings: Settings):
        """Override get_settings with DR settings"""

        def override_get_settings():
            return cdn_override_settings

        app.dependency_overrides[get_settings] = override_get_settings
        yield
        app.dependency_overrides.pop(get_settings)

    @pytest.fixture
    async def override_media_storage(self, app: FastAPI, media_storage_client_dr):
        """Inject media storage client into app with DR settings"""

        def override_get_media_storage():
            return media_storage_client_dr

        app.dependency_overrides[get_media_storage] = override_get_media_storage
        yield
        app.dependency_overrides.pop(get_media_storage)

    @pytest.mark.usefixtures("override_media_storage")
    async def test_generate_presigned_media_url(
        self, client: TestClient, tom: User, media_storage_config_dr: StorageConfig
    ):
        client.login(tom)
        resp = await client.post(self.upload_media_url, data={"file_name": FILE_KEY})

        assert resp.status_code == http.HTTPStatus.OK
        result = resp.json()["result"]
        assert media_storage_config_dr.bucket_override in result["uploadUrl"]
        expected_url = f"https://{media_storage_config_dr.domain}/{result['fields']['key']}"
        assert result["url"] == expected_url

    @pytest.mark.usefixtures("override_app_with_dr_settings")
    async def test_generate_presigned_answer_url(
        self,
        client: TestClient,
        tom: User,
        applet_one: AppletFull,
        answer_storage_client_dr: StorageClient,
        cdn_override_settings: Settings,
    ):
        client.login(tom)

        expected_key = answer_storage_client_dr.generate_key(
            FileScopeEnum.ANSWER, f"{tom.id}/{applet_one.id}", self.file_id
        )
        resp = await client.post(self.answer_upload_url.format(applet_id=applet_one.id), data={"file_id": self.file_id})

        assert resp.status_code == http.HTTPStatus.OK
        result = resp.json()["result"]

        assert result["fields"]["key"] == expected_key
        assert cdn_override_settings.cdn.bucket_answer in result["url"]
        assert cdn_override_settings.cdn.bucket_answer_override not in result["url"]
        assert result["url"] == answer_storage_client_dr.generate_private_url(expected_key)
        assert cdn_override_settings.cdn.bucket_answer_override in result["uploadUrl"]
