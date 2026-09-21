import http

import pytest
from botocore.exceptions import ClientError
from pytest_mock import MockerFixture

from apps.applets.domain.applet_full import AppletFull
from apps.audit import EventAction, EventOutcome
from apps.shared.exception import AccessDeniedError
from apps.shared.test import BaseTest
from apps.shared.test.client import TestClient
from apps.users.domain import User


@pytest.mark.usefixtures("cdn_settings", "override_app_settings", "s3_resource")
class TestFileDownloadAudit(BaseTest):
    answer_download_url = "/file/{applet_id}/download"
    presign_url = "/file/{applet_id}/presign"

    async def test_file_download_success_logs_file_path(
        self,
        client: TestClient,
        tom: User,
        applet_one: AppletFull,
        mocker: MockerFixture,
    ):
        mocker.patch(
            "infrastructure.storage.storage_client.StorageClient.download",
            return_value=(iter(("a", "b")), "txt"),
        )
        audit_log = mocker.patch("apps.file.api.file.log")
        client.login(tom)

        key = "1693560380000/c60859c4-6f5f-4390-a572-da85fcd59709"
        response = await client.post(
            self.answer_download_url.format(applet_id=applet_one.id),
            data={"key": key},
        )

        assert response.status_code == http.HTTPStatus.OK
        audit_log.assert_awaited_once()
        event = audit_log.call_args[0][0]
        assert event.user_id == tom.id
        assert event.event_action == EventAction.APPLET_ANSWER_FILE_DOWNLOAD
        assert event.event_outcome == EventOutcome.SUCCESS
        assert event.curious_applet_id == [applet_one.id]
        assert event.file_path == key

    async def test_file_download_failure_404_logs_event(
        self,
        client: TestClient,
        tom: User,
        applet_one: AppletFull,
        mocker: MockerFixture,
    ):
        mocker.patch(
            "botocore.client.BaseClient._make_api_call",
            side_effect=ClientError({"Error": {"Code": "404"}}, "Not Found"),
        )
        audit_log = mocker.patch("apps.file.api.file.log")
        client.login(tom)

        key = "1693560380000/c60859c4-6f5f-4390-a572-da85fcd59709"
        response = await client.post(
            self.answer_download_url.format(applet_id=applet_one.id),
            data={"key": key},
        )

        assert response.status_code == http.HTTPStatus.NOT_FOUND
        audit_log.assert_awaited_once()
        event = audit_log.call_args[0][0]
        assert event.user_id == tom.id
        assert event.event_action == EventAction.APPLET_ANSWER_FILE_DOWNLOAD
        assert event.event_outcome == EventOutcome.FAILURE
        assert event.curious_applet_id == [applet_one.id]
        assert event.file_path == key

    async def test_presign_success_fan_out_per_url(
        self,
        client: TestClient,
        tom: User,
        applet_one: AppletFull,
        mocker: MockerFixture,
    ):
        audit_log = mocker.patch("apps.file.api.file.log")
        client.login(tom)

        key = "1693560380000/c60859c4-6f5f-4390-a572-da85fcd59709"
        urls = [
            f"s3://bucket/mindlogger/answer/{tom.id}/{applet_one.id}/{key}-a",
            f"s3://bucket/mindlogger/answer/{tom.id}/{applet_one.id}/{key}-b",
            f"s3://bucket/mindlogger/answer/{tom.id}/{applet_one.id}/{key}-c",
        ]
        response = await client.post(
            self.presign_url.format(applet_id=applet_one.id),
            data={"privateUrls": urls},
        )

        assert response.status_code == http.HTTPStatus.OK
        assert audit_log.await_count == 3
        for call, url in zip(audit_log.await_args_list, urls):
            event = call.args[0]
            assert event.user_id == tom.id
            assert event.event_action == EventAction.APPLET_ANSWER_FILE_DOWNLOAD
            assert event.event_outcome == EventOutcome.SUCCESS
            assert event.curious_applet_id == [applet_one.id]
            assert event.file_path == url

    async def test_presign_success_single_url(
        self,
        client: TestClient,
        tom: User,
        applet_one: AppletFull,
        mocker: MockerFixture,
    ):
        audit_log = mocker.patch("apps.file.api.file.log")
        client.login(tom)

        key = "1693560380000/c60859c4-6f5f-4390-a572-da85fcd59709"
        url = f"s3://bucket/mindlogger/answer/{tom.id}/{applet_one.id}/{key}"
        response = await client.post(
            self.presign_url.format(applet_id=applet_one.id),
            data={"privateUrls": [url]},
        )

        assert response.status_code == http.HTTPStatus.OK
        audit_log.assert_awaited_once()
        event = audit_log.call_args[0][0]
        assert event.event_action == EventAction.APPLET_ANSWER_FILE_DOWNLOAD
        assert event.event_outcome == EventOutcome.SUCCESS
        assert event.curious_applet_id == [applet_one.id]
        assert event.file_path == url

    async def test_presign_failure_emits_per_url(
        self,
        client: TestClient,
        tom: User,
        applet_one: AppletFull,
        mocker: MockerFixture,
    ):
        mocker.patch(
            "apps.file.api.file.get_presign_service",
            side_effect=AccessDeniedError(),
        )
        audit_log = mocker.patch("apps.file.api.file.log")
        client.login(tom)

        urls = ["s3://bucket/a", "s3://bucket/b"]
        response = await client.post(
            self.presign_url.format(applet_id=applet_one.id),
            data={"privateUrls": urls},
        )

        assert response.status_code != http.HTTPStatus.OK
        assert audit_log.await_count == 2
        for call, url in zip(audit_log.await_args_list, urls):
            event = call.args[0]
            assert event.user_id == tom.id
            assert event.event_action == EventAction.APPLET_ANSWER_FILE_DOWNLOAD
            assert event.event_outcome == EventOutcome.FAILURE
            assert event.curious_applet_id == [applet_one.id]
            assert event.file_path == url
