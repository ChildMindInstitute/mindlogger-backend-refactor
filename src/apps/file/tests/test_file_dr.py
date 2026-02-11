import http

import pytest
from fastapi import FastAPI

from apps.file.tests import FILE_KEY, MEDIA_BUCKET_NAME_DR, MEDIA_STORAGE_ADDRESS
from apps.shared.test import BaseTest
from apps.shared.test.client import TestClient
from apps.users import User
from infrastructure.storage.storage import get_media_storage


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
    async def override_media_storage(self, app: FastAPI, media_storage_client_dr):
        """Inject media storage client into app"""

        def override_get_media_storage():
            return media_storage_client_dr

        app.dependency_overrides[get_media_storage] = override_get_media_storage
        yield
        app.dependency_overrides.pop(get_media_storage)

    @pytest.mark.usefixtures("override_media_storage")
    async def test_generate_presigned_media_url(self, client: TestClient, tom: User):
        client.login(tom)
        resp = await client.post(self.upload_media_url, data={"file_name": FILE_KEY})

        assert resp.status_code == http.HTTPStatus.OK
        result = resp.json()["result"]
        assert MEDIA_BUCKET_NAME_DR in result["uploadUrl"]
        assert result["url"] == f"{MEDIA_STORAGE_ADDRESS}/{result['fields']['key']}"
