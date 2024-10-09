import copy
import http
import json
import uuid
from unittest.mock import ANY

import pytest
from firebase_admin.exceptions import NotFoundError as FireBaseNotFoundError
from pytest_mock import MockerFixture
from sqlalchemy.ext.asyncio import AsyncSession

from apps.activities.domain.activity_create import ActivityItemCreate
from apps.activities.domain.activity_update import ActivityItemUpdate
from apps.activities.domain.response_type_config import ResponseType
from apps.activities.errors import (
    AssessmentLimitExceed,
    DuplicateActivityFlowNameError,
    DuplicateActivityItemNameNameError,
    DuplicateActivityNameError,
    DuplicatedActivitiesError,
    DuplicatedActivityFlowsError,
    FlowItemActivityKeyNotFoundError,
)
from apps.activity_assignments.crud.assignments import ActivityAssigmentCRUD
from apps.activity_assignments.db.schemas import ActivityAssigmentSchema
from apps.applets.domain.applet_create_update import AppletCreate, AppletReportConfiguration, AppletUpdate
from apps.applets.domain.applet_full import AppletFull
from apps.applets.domain.base import AppletReportConfigurationBase, Encryption
from apps.applets.errors import AppletAlreadyExist, AppletVersionNotFoundError
from apps.applets.service.applet import AppletService
from apps.shared.exception import NotFoundError
from apps.shared.test.client import TestClient
from apps.users.domain import User
from apps.workspaces.domain.constants import Role
from apps.workspaces.errors import AppletCreationAccessDenied, AppletEncryptionUpdateDenied
from infrastructure.utility import FCMNotificationTest


class TestApplet:
    login_url = "/auth/login"
    applet_list_url = "applets"
    applet_create_url = "workspaces/{owner_id}/applets"
    applet_detail_url = f"{applet_list_url}/{{pk}}"
    applet_duplicate_url = f"{applet_detail_url}/duplicate"
    applet_report_config_url = f"{applet_detail_url}/report_configuration"
    activity_report_config_url = f"{applet_detail_url}/activities/{{activity_id}}/report_configuration"
    flow_report_config_url = f"{applet_detail_url}/flows/{{flow_id}}/report_configuration"
    applet_publish_url = f"{applet_detail_url}/publish"
    applet_conceal_url = f"{applet_detail_url}/conceal"
    applet_set_encryption_url = f"{applet_detail_url}/encryption"
    applet_unique_name_url = f"{applet_list_url}/unique_name"
    histories_url = f"{applet_detail_url}/versions"
    history_url = f"{applet_detail_url}/versions/{{version}}"
    history_changes_url = f"{applet_detail_url}/versions/{{version}}/changes"
    applet_base_info_url = f"{applet_detail_url}/base_info"
    access_link_url = f"{applet_detail_url}/access_link"

    public_applet_detail_url = "/public/applets/{key}"
    public_applet_base_info_url = f"{public_applet_detail_url}/base_info"

    async def test_create_applet_with_minimal_data(
        self, client: TestClient, tom: User, applet_minimal_data: AppletCreate
    ):
        client.login(tom)
        response = await client.post(
            self.applet_create_url.format(owner_id=tom.id),
            data=applet_minimal_data,
        )
        assert response.status_code == http.HTTPStatus.CREATED, response.json()
        result = response.json()["result"]
        # TODO: check response?
        assert result

        response = await client.get(self.applet_detail_url.format(pk=response.json()["result"]["id"]))
        assert response.status_code == http.HTTPStatus.OK
        result = response.json()["result"]
        assert result["streamIpAddress"] == str(applet_minimal_data.stream_ip_address)
        assert result["streamPort"] == applet_minimal_data.stream_port
        assert result["displayName"] == applet_minimal_data.display_name
        assert result["image"] == applet_minimal_data.image
        assert result["watermark"] == applet_minimal_data.watermark
        assert result["link"] == applet_minimal_data.link
        assert result["pinnedAt"] == applet_minimal_data.pinned_at
        assert result["retentionPeriod"] == applet_minimal_data.retention_period
        assert result["retentionType"] == applet_minimal_data.retention_type
        assert result["reportServerIp"] == applet_minimal_data.report_server_ip
        assert result["reportPublicKey"] == applet_minimal_data.report_public_key
        assert result["reportRecipients"] == applet_minimal_data.report_recipients

    async def test_create_applet_with_activities_auto_assign(
        self, client: TestClient, tom: User, applet_minimal_data: AppletCreate
    ):
        client.login(tom)
        applet_minimal_data.activities[0].auto_assign = True
        response = await client.post(
            self.applet_create_url.format(owner_id=tom.id),
            data=applet_minimal_data,
        )
        assert response.status_code == http.HTTPStatus.CREATED, response.json()
        result = response.json()["result"]
        assert len(result["activities"]) == 1
        assert result["activities"][0]["autoAssign"] is True

    async def test_create_applet_without_activities_auto_assign(
        self, client: TestClient, tom: User, applet_minimal_data: AppletCreate
    ):
        client.login(tom)
        applet_minimal_data.activities[0].auto_assign = False
        response = await client.post(
            self.applet_create_url.format(owner_id=tom.id),
            data=applet_minimal_data,
        )
        assert response.status_code == http.HTTPStatus.CREATED, response.json()
        result = response.json()["result"]
        assert len(result["activities"]) == 1
        assert result["activities"][0]["autoAssign"] is False

    async def test_creating_applet_failed_by_duplicate_activity_name(
        self, client: TestClient, tom: User, applet_minimal_data: AppletCreate
    ):
        client.login(tom)
        data = applet_minimal_data.copy(deep=True)
        data.activities.append(data.activities[0])
        response = await client.post(self.applet_create_url.format(owner_id=tom.id), data=data)
        assert response.status_code == http.HTTPStatus.UNPROCESSABLE_ENTITY
        result = response.json()["result"]
        assert len(result) == 1
        assert result[0]["message"] == DuplicateActivityNameError.message

    async def test_creating_applet_failed_by_duplicate_activity_item_name(
        self, client: TestClient, tom: User, applet_minimal_data: AppletCreate
    ):
        client.login(tom)
        data = applet_minimal_data.copy(deep=True)
        data.activities[0].items.append(data.activities[0].items[0])
        response = await client.post(self.applet_create_url.format(owner_id=tom.id), data=data)
        assert response.status_code == http.HTTPStatus.UNPROCESSABLE_ENTITY
        result = response.json()["result"]
        assert len(result) == 1
        assert result[0]["message"] == DuplicateActivityItemNameNameError.message

    @pytest.mark.parametrize("applet_name", ("duplicate name", "DUPLICATE NAME", "duPlicate Name"))
    async def test_create_duplicate_name_applet(
        self, client: TestClient, tom: User, applet_minimal_data: AppletCreate, applet_name: str
    ):
        client.login(tom)
        data = applet_minimal_data.copy(deep=True)
        data.display_name = applet_name
        response = await client.post(self.applet_create_url.format(owner_id=tom.id), data=data)
        assert response.status_code == http.HTTPStatus.CREATED
        response = await client.post(self.applet_create_url.format(owner_id=tom.id), data=data)
        assert response.status_code == http.HTTPStatus.BAD_REQUEST
        result = response.json()["result"]
        assert len(result) == 1
        assert response.json()["result"][0]["message"] == AppletAlreadyExist.message

    async def test_update_applet(
        self, client: TestClient, tom: User, device_tom: str, applet_one: AppletFull, fcm_client: FCMNotificationTest
    ):
        client.login(tom)
        update_data = AppletUpdate(**applet_one.dict())

        response = await client.put(
            self.applet_detail_url.format(pk=applet_one.id),
            data=update_data,
        )
        assert response.status_code == http.HTTPStatus.OK, response.json()

        assert device_tom in fcm_client.notifications
        assert len(fcm_client.notifications[device_tom]) == 1
        notification = json.loads(fcm_client.notifications[device_tom][0])
        assert notification["title"] == "Applet is updated."

    async def test_update_applet_change_activities_auto_assign(
        self, client: TestClient, tom: User, applet_one: AppletFull
    ):
        client.login(tom)
        assert applet_one.activities[0].auto_assign is True
        update_data = AppletUpdate(**applet_one.dict())
        update_data.activities[0].auto_assign = False

        response = await client.put(
            self.applet_detail_url.format(pk=applet_one.id),
            data=update_data,
        )
        assert response.status_code == http.HTTPStatus.OK, response.json()
        result = response.json()["result"]
        assert result["activities"][0]["autoAssign"] is False

    async def test_update_applet_keep_activities_auto_assign(
        self, client: TestClient, tom: User, applet_one: AppletFull
    ):
        client.login(tom)
        assert applet_one.activities[0].auto_assign is True
        update_data = AppletUpdate(**applet_one.dict())
        update_data.activities[0].auto_assign = None

        response = await client.put(
            self.applet_detail_url.format(pk=applet_one.id),
            data=update_data,
        )
        assert response.status_code == http.HTTPStatus.OK, response.json()
        result = response.json()["result"]
        assert result["activities"][0]["autoAssign"] is True

    async def test_update_applet__add_stream_settings(self, client: TestClient, applet_one: AppletFull, tom: User):
        client.login(tom)
        update_data = AppletUpdate(**applet_one.dict())
        update_data.stream_enabled = True
        update_data.stream_ip_address = "127.0.0.1"  # type: ignore[assignment]
        update_data.stream_port = 8001
        response = await client.put(self.applet_detail_url.format(pk=applet_one.id), data=update_data)
        assert response.status_code == http.HTTPStatus.OK
        response = await client.get(self.applet_detail_url.format(pk=applet_one.id))
        assert response.status_code == http.HTTPStatus.OK
        assert response.json()["result"]["streamEnabled"]
        assert response.json()["result"]["streamIpAddress"] == str(update_data.stream_ip_address)
        assert response.json()["result"]["streamPort"] == update_data.stream_port

    async def test_update_applet_duplicate_name_activity(
        self, client: TestClient, tom: User, device_tom: str, applet_one: AppletFull
    ):
        client.login(tom)
        update_data = AppletUpdate(**applet_one.dict())
        update_data.activities.append(update_data.activities[0])

        response = await client.put(
            self.applet_detail_url.format(pk=applet_one.id),
            data=update_data,
        )
        assert response.status_code == http.HTTPStatus.UNPROCESSABLE_ENTITY
        result = response.json()["result"]
        assert len(result) == 1
        assert result[0]["message"] == DuplicateActivityNameError.message

    async def test_duplicate_applet(
        self, client: TestClient, tom: User, applet_one: AppletFull, encryption: Encryption
    ):
        client.login(tom)
        new_name = "New Name"
        response = await client.post(
            self.applet_duplicate_url.format(pk=applet_one.id),
            data=dict(display_name=new_name, encryption=encryption.dict()),
        )
        assert response.status_code == http.HTTPStatus.CREATED
        assert response.json()["result"]["displayName"] == new_name

    async def test_duplicate_applet_default_exclude_report_server_config(
        self, client: TestClient, tom: User, applet_one: AppletFull, encryption: Encryption, session: AsyncSession
    ):
        await AppletService(session, tom.id).set_report_configuration(
            applet_one.id,
            AppletReportConfiguration(
                report_server_ip="ipaddress",
                report_public_key="public key",
                report_recipients=["recipient1", "recipient1"],
                report_include_user_id=True,
                report_include_case_id=True,
                report_email_body="email body",
            ),
        )

        client.login(tom)
        new_name = "New Name"
        response = await client.post(
            self.applet_duplicate_url.format(pk=applet_one.id),
            data=dict(display_name=new_name, encryption=encryption.dict()),
        )
        assert response.status_code == http.HTTPStatus.CREATED

        result = response.json()["result"]
        assert result["displayName"] == new_name
        assert result["reportServerIp"] == ""
        assert result["reportPublicKey"] == ""
        assert result["reportRecipients"] == []
        assert result["reportIncludeUserId"] is False
        assert result["reportIncludeCaseId"] is False
        assert result["reportEmailBody"] == ""

    async def test_duplicate_applet_include_report_server_config(
        self, client: TestClient, tom: User, applet_one: AppletFull, encryption: Encryption, session: AsyncSession
    ):
        await AppletService(session, tom.id).set_report_configuration(
            applet_one.id,
            AppletReportConfiguration(
                report_server_ip="ipaddress",
                report_public_key="public key",
                report_recipients=["recipient1", "recipient1"],
                report_include_user_id=True,
                report_include_case_id=True,
                report_email_body="email body",
            ),
        )

        client.login(tom)
        new_name = "New Name"
        response = await client.post(
            self.applet_duplicate_url.format(pk=applet_one.id),
            data=dict(display_name=new_name, encryption=encryption.dict(), include_report_server=True),
        )
        assert response.status_code == http.HTTPStatus.CREATED

        result = response.json()["result"]
        assert result["displayName"] == new_name
        assert result["reportServerIp"] == "ipaddress"
        assert result["reportPublicKey"] == "public key"
        assert result["reportIncludeUserId"] is True
        assert result["reportIncludeCaseId"] is True
        assert result["reportEmailBody"] == "email body"

        # Recipients are excluded
        assert result["reportRecipients"] == []

    async def test_duplicate_applet_name_already_exists(
        self, client: TestClient, tom: User, applet_one: AppletFull, encryption: Encryption
    ):
        client.login(tom)
        response = await client.post(
            self.applet_duplicate_url.format(pk=applet_one.id),
            data=dict(display_name=applet_one.display_name, encryption=encryption.dict()),
        )
        assert response.status_code == http.HTTPStatus.BAD_REQUEST
        result = response.json()["result"]
        assert len(result) == 1
        assert result[0]["message"] == AppletAlreadyExist.message

    async def test_set_applet_report_configuration(self, client: TestClient, tom: User, applet_one: AppletFull):
        client.login(tom)
        text_with_script_inside = "One <script>alert('test')</script> Two"
        sanitized_text = "One  Two"
        report_configuration = dict(
            report_server_ip="ipaddress",
            report_public_key="public key",
            report_recipients=["recipient1", "recipient1"],
            report_include_user_id=True,
            report_include_case_id=True,
            report_email_body=text_with_script_inside,
        )

        response = await client.post(
            self.applet_report_config_url.format(
                pk=applet_one.id,
            ),
            report_configuration,
        )
        assert response.status_code == http.HTTPStatus.OK, response.json()

        response = await client.get(self.applet_detail_url.format(pk=applet_one.id))
        assert response.status_code == http.HTTPStatus.OK
        assert response.json()["result"]["reportServerIp"] == report_configuration["report_server_ip"]
        assert response.json()["result"]["reportPublicKey"] == report_configuration["report_public_key"]
        assert response.json()["result"]["reportRecipients"] == report_configuration["report_recipients"]
        assert response.json()["result"]["reportIncludeUserId"] == report_configuration["report_include_user_id"]
        assert response.json()["result"]["reportIncludeCaseId"] == report_configuration["report_include_case_id"]
        assert response.json()["result"]["reportEmailBody"] == sanitized_text

    async def test_publish_conceal_applet(
        self, client: TestClient, tom: User, applet_one: AppletFull, superadmin: User
    ):
        # NOTE: only superadmin can publish an applet
        client.login(superadmin)
        response = await client.post(self.applet_publish_url.format(pk=applet_one.id))
        assert response.status_code == http.HTTPStatus.OK, response.json()

        client.login(tom)
        response = await client.get(self.applet_detail_url.format(pk=applet_one.id))
        assert response.status_code == http.HTTPStatus.OK
        assert response.json()["result"]["isPublished"] is True

        # NOTE: only superadmin can conceal an applet
        client.login(superadmin)
        response = await client.post(self.applet_conceal_url.format(pk=applet_one.id))
        assert response.status_code == http.HTTPStatus.OK, response.json()

        client.login(tom)
        response = await client.get(self.applet_detail_url.format(pk=applet_one.id))
        assert response.status_code == http.HTTPStatus.OK
        assert response.json()["result"]["isPublished"] is False

    async def test_set_encryption(
        self, client: TestClient, tom: User, applet_one_no_encryption: AppletFull, encryption: Encryption
    ):
        client.login(tom)

        assert applet_one_no_encryption.encryption is None
        response = await client.post(
            self.applet_set_encryption_url.format(pk=applet_one_no_encryption.id),
            data=encryption,
        )
        assert response.status_code == http.HTTPStatus.OK
        result = response.json()["result"]
        assert result["publicKey"] == encryption.public_key
        assert result["prime"] == encryption.prime
        assert result["base"] == encryption.base
        assert result["accountId"] == encryption.account_id
        resp = await client.get(
            self.applet_detail_url.format(pk=applet_one_no_encryption.id),
        )
        assert resp.status_code == http.HTTPStatus.OK

    async def test_set_encryption__encryption_already_set(
        self, client: TestClient, tom: User, applet_one: AppletFull, encryption: Encryption
    ):
        client.login(tom)
        response = await client.post(self.applet_set_encryption_url.format(pk=applet_one.id), data=encryption)
        assert response.status_code == http.HTTPStatus.FORBIDDEN
        result = response.json()["result"]
        assert len(result) == 1
        assert result[0]["message"] == AppletEncryptionUpdateDenied.message

    async def test_applet_list(self, client: TestClient, tom: User, applet_one: AppletFull, applet_two: AppletFull):
        client.login(tom)
        response = await client.get(self.applet_list_url)

        assert response.status_code == http.HTTPStatus.OK, response.json()
        assert len(response.json()["result"]) == 2
        exp_ids = {str(applet_one.id), str(applet_two.id)}
        act_ids = set(i["id"] for i in response.json()["result"])
        assert exp_ids == act_ids

    async def test_applet_delete(
        self, client: TestClient, tom: User, applet_one: AppletFull, device_tom: str, fcm_client: FCMNotificationTest
    ):
        client.login(tom)
        response = await client.delete(
            self.applet_detail_url.format(pk=applet_one.id),
        )

        assert response.status_code == http.HTTPStatus.NO_CONTENT

        # TODO: move to the fixtures
        assert device_tom in fcm_client.notifications
        assert len(fcm_client.notifications[device_tom]) == 1
        notification = json.loads(fcm_client.notifications[device_tom][0])
        assert notification["title"] == "Applet is deleted."

    async def test_applet_delete__applet_does_not_exists(self, client: TestClient, tom: User, uuid_zero: uuid.UUID):
        client.login(tom)
        response = await client.delete(
            self.applet_detail_url.format(pk=uuid_zero),
        )

        assert response.status_code == http.HTTPStatus.NOT_FOUND

    async def test_applet_delete_by_manager(self, client: TestClient, applet_one_lucy_manager: AppletFull, lucy: User):
        client.login(lucy)
        response = await client.delete(
            self.applet_detail_url.format(pk=applet_one_lucy_manager.id),
        )

        assert response.status_code == http.HTTPStatus.NO_CONTENT

    async def test_applet_delete_by_coordinator(
        self, client: TestClient, applet_one_lucy_coordinator: AppletFull, lucy: User
    ):
        client.login(lucy)
        response = await client.delete(
            self.applet_detail_url.format(pk=applet_one_lucy_coordinator.id),
        )

        assert response.status_code == http.HTTPStatus.FORBIDDEN

    async def test_applet_list_with_limit(self, client: TestClient, tom: User, applet_one: AppletFull):
        client.login(tom)
        response = await client.get(self.applet_list_url, dict(ordering="id", limit=1))

        assert response.status_code == http.HTTPStatus.OK
        assert len(response.json()["result"]) == 1
        assert response.json()["result"][0]["id"] == str(applet_one.id)

    async def test_applet_detail(self, client: TestClient, tom: User, applet_one_with_flow: AppletFull):
        client.login(tom)
        response = await client.get(self.applet_detail_url.format(pk=applet_one_with_flow.id))
        assert response.status_code == http.HTTPStatus.OK
        result = response.json()["result"]
        assert result["displayName"] == applet_one_with_flow.display_name
        assert result["ownerId"] == str(tom.id)
        assert len(result["activities"]) == 1
        assert len(result["activityFlows"]) == 1
        assert response.json()["respondentMeta"]["nickname"] == tom.get_full_name()

    async def test_public_applet_detail(self, client: TestClient, applet_one_with_public_link: AppletFull):
        response = await client.get(self.public_applet_detail_url.format(key=applet_one_with_public_link.link))
        assert response.status_code == http.HTTPStatus.OK
        result = response.json()["result"]
        assert result["displayName"] == applet_one_with_public_link.display_name
        assert result["ownerId"] == "7484f34a-3acc-4ee6-8a94-fd7299502fa1"
        assert len(result["activities"]) == 1

    async def test_create_applet__initial_version_is_created_in_applet_history(
        self, client: TestClient, tom: User, applet_minimal_data: AppletCreate
    ):
        client.login(tom)
        response = await client.post(
            self.applet_create_url.format(owner_id=tom.id),
            data=applet_minimal_data,
        )
        assert response.status_code == http.HTTPStatus.CREATED
        version = response.json()["result"]["version"]
        applet_id = response.json()["result"]["id"]

        response = await client.get(self.histories_url.format(pk=applet_id))

        assert response.status_code == http.HTTPStatus.OK
        versions = response.json()["result"]
        assert len(versions) == 1
        assert versions[0]["version"] == version

    async def test_get_versions_for_not_existed_applet(self, client: TestClient, tom: User, uuid_zero: uuid.UUID):
        client.login(tom)
        response = await client.get(self.histories_url.format(pk=uuid_zero))
        assert response.status_code == http.HTTPStatus.NOT_FOUND

    async def test_update_applet__applet_history_is_updated(
        self, client: TestClient, tom: User, applet_one: AppletFull, applet_minimal_data: AppletCreate
    ):
        client.login(tom)
        # first change patch version
        update_data_patch = applet_one.dict()
        update_data_patch["description"] = {"en": "description"}
        response = await client.put(
            self.applet_detail_url.format(pk=applet_one.id),
            data=update_data_patch,
        )
        assert response.status_code == http.HTTPStatus.OK
        assert response.json()["result"]["version"] == "1.1.1"

        # second change minor version
        update_data_minor = copy.deepcopy(update_data_patch)
        item = applet_minimal_data.activities[0].items[0].copy(deep=True)
        item.name = item.name + "second"
        update_data_minor["activities"][0]["items"].append(item.dict())
        response = await client.put(
            self.applet_detail_url.format(pk=applet_one.id),
            data=update_data_minor,
        )
        assert response.status_code == http.HTTPStatus.OK
        assert response.json()["result"]["version"] == "1.2.0"

        # third change major version
        update_data_major = copy.deepcopy(update_data_minor)
        activity = applet_minimal_data.activities[0].copy(deep=True)
        activity.name = activity.name + "second"
        update_data_major["activities"].append(activity.dict())
        response = await client.put(
            self.applet_detail_url.format(pk=applet_one.id),
            data=update_data_major,
        )
        assert response.status_code == http.HTTPStatus.OK
        assert response.json()["result"]["version"] == "2.0.0"

        # check all versions
        response = await client.get(self.histories_url.format(pk=applet_one.id))
        assert response.status_code == http.HTTPStatus.OK
        versions = response.json()["result"]
        assert len(versions) == 4
        assert versions[0]["version"] == "2.0.0"
        assert versions[1]["version"] == "1.2.0"
        assert versions[2]["version"] == "1.1.1"
        assert versions[3]["version"] == "1.1.0"

        # check history by version
        response = await client.get(self.history_url.format(pk=applet_one.id, version="2.0.0"))
        assert response.status_code == http.HTTPStatus.OK, response.json()
        applet = response.json()["result"]
        assert applet["version"] == "2.0.0"

    async def test_get_history_version__applet_version_does_not_exist(
        self, client: TestClient, tom: User, applet_one: AppletFull
    ):
        client.login(tom)
        response = await client.get(self.history_url.format(pk=applet_one.id, version="0.0.0"))
        assert response.status_code == http.HTTPStatus.NOT_FOUND

    async def test_get_history_changes__applet_display_name_is_updated(
        self, client: TestClient, tom: User, applet_one: AppletFull
    ):
        # NOTE: Only simple test is tested here. All other history changes are tested in unit tests
        client.login(tom)
        update_data = AppletUpdate(**applet_one.dict())
        new_display_name = "new display name"
        update_data.display_name = new_display_name
        response = await client.put(self.applet_detail_url.format(pk=applet_one.id), data=update_data)
        assert response.status_code == http.HTTPStatus.OK
        assert response.json()["result"]["displayName"] == new_display_name

        version = response.json()["result"]["version"]
        applet_id = response.json()["result"]["id"]

        response = await client.get(self.history_changes_url.format(pk=applet_id, version=version))
        assert response.status_code == http.HTTPStatus.OK
        assert response.json()["result"]["displayName"] == f"Applet {new_display_name} updated"

    async def test_get_applet_unique_name__name_already_used(
        self, client: TestClient, tom: User, applet_one: AppletFull
    ):
        client.login(tom)

        response = await client.post(self.applet_unique_name_url, data=dict(name=applet_one.display_name))

        assert response.status_code == http.HTTPStatus.OK
        assert response.json()["result"]["name"] == f"{applet_one.display_name} (1)"

    async def test_get_applet_unique_name__name_already_used_case_insensitive(
        self, client: TestClient, tom: User, applet_one: AppletFull
    ):
        client.login(tom)

        name = applet_one.display_name.upper()
        response = await client.post(self.applet_unique_name_url, data=dict(name=name))

        assert response.status_code == http.HTTPStatus.OK
        assert response.json()["result"]["name"] == f"{name} (1)"

    async def test_get_applet_activities_info(
        self,
        client: TestClient,
        tom: User,
        applet_minimal_data: AppletCreate,
        multi_select_item_create: ActivityItemCreate,
    ):
        client.login(tom)
        # create applet with minimal data
        data = applet_minimal_data.copy(deep=True)
        multi_select_item_create.is_hidden = True
        data.activities[0].items.append(multi_select_item_create)
        response = await client.post(self.applet_create_url.format(owner_id=tom.id), data=data)
        assert response.status_code == http.HTTPStatus.CREATED
        assert len(response.json()["result"]["activities"][0]["items"]) == 2

        new_applet_id = response.json()["result"]["id"]
        response = await client.get(self.applet_base_info_url.format(pk=new_applet_id))
        assert response.status_code == http.HTTPStatus.OK
        assert response.json()["result"]["displayName"] == data.display_name
        # check if hidden item is not shown
        assert ResponseType.SINGLESELECT in response.json()["result"]["activities"][0]["containsResponseTypes"]
        assert ResponseType.MULTISELECT not in response.json()["result"]["activities"][0]["containsResponseTypes"]
        assert response.json()["result"]["activities"][0]["itemCount"] == 1

    async def test_get_public_applet_activities_info(
        self,
        client: TestClient,
        tom: User,
        applet_one_with_public_link: AppletFull,
        multi_select_item_create: ActivityItemCreate,
    ):
        client.login(tom)
        update_data = AppletUpdate(**applet_one_with_public_link.dict())
        multi_select_item_create.is_hidden = True
        update_data.activities[0].items.append(ActivityItemUpdate(**multi_select_item_create.dict()))
        resp = await client.put(self.applet_detail_url.format(pk=applet_one_with_public_link.id), data=update_data)
        assert resp.status_code == http.HTTPStatus.OK
        assert resp.json()["result"]["activities"][0]["items"][1]["isHidden"]
        assert resp.json()["result"]["activities"][0]["items"][1]["responseType"] == ResponseType.MULTISELECT

        response = await client.get(self.public_applet_base_info_url.format(key=applet_one_with_public_link.link))
        assert response.status_code == http.HTTPStatus.OK
        assert response.json()["result"]["displayName"] == applet_one_with_public_link.display_name
        assert ResponseType.SINGLESELECT in response.json()["result"]["activities"][0]["containsResponseTypes"]
        assert ResponseType.MULTISELECT not in response.json()["result"]["activities"][0]["containsResponseTypes"]
        assert response.json()["result"]["activities"][0]["itemCount"] == 1

    @pytest.mark.usefixtures("applet_one_lucy_manager")
    async def test_create_applet_in_another_workspace_not_owner(self, client, applet_minimal_data, tom, lucy):
        client.login(lucy)
        response = await client.post(
            self.applet_create_url.format(owner_id=tom.id),
            data=applet_minimal_data,
        )
        assert response.status_code == http.HTTPStatus.CREATED

    async def test_create_applet_in_another_workspace_not_owner_user_is_not_invited(
        self, client, applet_minimal_data, bob, lucy
    ):
        client.login(lucy)
        response = await client.post(
            self.applet_create_url.format(owner_id=bob.id),
            data=applet_minimal_data,
        )
        assert response.status_code == http.HTTPStatus.FORBIDDEN
        result = response.json()["result"]
        assert len(result) == 1
        assert result[0]["message"] == AppletCreationAccessDenied.message

    async def test_create_applet_in_another_workspace_not_owner_user_does_not_have_role_to_create_applet(
        self, client, applet_minimal_data, tom, bob
    ):
        client.login(bob)
        response = await client.post(
            self.applet_create_url.format(owner_id=tom.id),
            data=applet_minimal_data,
        )
        assert response.status_code == http.HTTPStatus.FORBIDDEN
        result = response.json()["result"]
        assert len(result) == 1
        assert result[0]["message"] == AppletCreationAccessDenied.message

    async def test_update_applet__firebase_error_muted(self, client, tom, applet_minimal_data, mocker, applet_one):
        client.login(tom)
        mocker.patch(
            "infrastructure.utility.notification_client.FCMNotificationTest.notify",
            side_effect=FireBaseNotFoundError(message="device id not found"),
        )
        resp = await client.put(self.applet_detail_url.format(pk=applet_one.id), data=applet_minimal_data)
        assert resp.status_code == http.HTTPStatus.OK

    async def test_update_report_config_for_activity__activity_from_another_applet(
        self, client: TestClient, tom: User, applet_one: AppletFull, applet_two, applet_report_configuration_data
    ):
        client.login(tom)
        resp = await client.put(
            self.activity_report_config_url.format(pk=applet_one.id, activity_id=applet_two.activities[0].id),
            data=applet_report_configuration_data,
        )
        assert resp.status_code == http.HTTPStatus.NOT_FOUND
        result = resp.json()["result"]
        assert len(result) == 1
        assert result[0]["message"] == NotFoundError.message

    async def test_update_report_config_for_activity__activity_does_not_exists(
        self,
        client: TestClient,
        tom: User,
        applet_one: AppletFull,
        applet_report_configuration_data: AppletReportConfigurationBase,
        uuid_zero: uuid.UUID,
    ):
        client.login(tom)
        resp = await client.put(
            self.activity_report_config_url.format(pk=applet_one.id, activity_id=uuid_zero),
            data=applet_report_configuration_data,
        )
        assert resp.status_code == http.HTTPStatus.NOT_FOUND
        result = resp.json()["result"]
        assert len(result) == 1
        assert result[0]["message"] == NotFoundError.message

    async def test_update_report_config_for_activity_flow__activity_from_another_applet(
        self,
        client: TestClient,
        tom: User,
        applet_one_with_flow: AppletFull,
        applet_two: AppletFull,
        applet_report_configuration_data: AppletReportConfigurationBase,
    ):
        client.login(tom)
        resp = await client.put(
            self.flow_report_config_url.format(pk=applet_two.id, flow_id=applet_one_with_flow.activity_flows[0].id),
            data=applet_report_configuration_data,
        )
        assert resp.status_code == http.HTTPStatus.NOT_FOUND
        result = resp.json()["result"]
        assert len(result) == 1
        assert result[0]["message"] == NotFoundError.message

    async def test_update_report_config_for_activity_flow__activity_does_not_exists(
        self,
        client: TestClient,
        tom: User,
        applet_one: AppletFull,
        applet_report_configuration_data: AppletReportConfigurationBase,
        uuid_zero: uuid.UUID,
    ):
        client.login(tom)
        resp = await client.put(
            self.flow_report_config_url.format(pk=applet_one.id, flow_id=uuid_zero),
            data=applet_report_configuration_data,
        )
        assert resp.status_code == http.HTTPStatus.NOT_FOUND
        result = resp.json()["result"]
        assert len(result) == 1
        assert result[0]["message"] == NotFoundError.message

    async def test_delete_applet__firebase_error_muted(
        self, client: TestClient, tom: User, mocker: MockerFixture, applet_one: AppletFull
    ):
        client.login(tom)
        mocker.patch(
            "infrastructure.utility.notification_client.FCMNotificationTest.notify",
            side_effect=FireBaseNotFoundError(message="device id not found"),
        )
        resp = await client.delete(self.applet_detail_url.format(pk=applet_one.id))
        assert resp.status_code == http.HTTPStatus.NO_CONTENT

    async def test_create_applet__duplicate_flow_name(
        self, client: TestClient, tom: User, applet_create_with_flow: AppletCreate
    ):
        client.login(tom)
        data = applet_create_with_flow.copy(deep=True)
        data.activity_flows.append(data.activity_flows[0])
        resp = await client.post(self.applet_create_url.format(owner_id=tom.id), data=data)
        assert resp.status_code == http.HTTPStatus.UNPROCESSABLE_ENTITY
        result = resp.json()["result"]
        assert len(result) == 1
        assert result[0]["message"] == DuplicateActivityFlowNameError.message

    async def test_create_applet__only_one_reviewable_activity_allowed(
        self, client: TestClient, tom: User, applet_minimal_data: AppletCreate
    ):
        client.login(tom)
        data = applet_minimal_data.copy(deep=True)
        data.activities[0].is_reviewable = True
        second_activity = data.activities[0].copy(deep=True)
        second_activity.name = data.activities[0].name + "second"
        data.activities.append(second_activity)
        resp = await client.post(self.applet_create_url.format(owner_id=tom.id), data=data)
        assert resp.status_code == http.HTTPStatus.UNPROCESSABLE_ENTITY
        result = resp.json()["result"]
        assert len(result) == 1
        assert result[0]["message"] == AssessmentLimitExceed.message

    async def test_update_applet__only_one_reviewable_activity_allowed(
        self, client: TestClient, tom: User, applet_one: AppletFull, applet_one_update_data: AppletUpdate
    ):
        client.login(tom)
        data = applet_one_update_data.copy(deep=True)
        data.activities[0].is_reviewable = True
        second_activity = data.activities[0].copy(deep=True)
        second_activity.name += "second"
        second_activity.id = None
        second_activity.items[0].id = None
        data.activities.append(second_activity)
        resp = await client.put(self.applet_detail_url.format(pk=applet_one.id), data=data)
        assert resp.status_code == http.HTTPStatus.UNPROCESSABLE_ENTITY
        result = resp.json()["result"]
        assert len(result) == 1
        assert result[0]["message"] == AssessmentLimitExceed.message

    async def test_update_applet__duplicated_activity(
        self, client: TestClient, tom: User, applet_one_update_data: AppletUpdate, applet_one: AppletFull
    ):
        client.login(tom)
        data = applet_one_update_data.copy(deep=True)
        second_activity = data.activities[0].copy(deep=True)
        second_activity.name += "second"
        request_data = data.dict()
        request_data["activities"].append(second_activity.dict())
        resp = await client.put(self.applet_detail_url.format(pk=applet_one.id), data=request_data)
        assert resp.status_code == http.HTTPStatus.UNPROCESSABLE_ENTITY
        result = resp.json()["result"]
        assert len(result) == 1
        assert result[0]["message"] == DuplicatedActivitiesError.message

    async def test_update_applet__duplicate_flow_name(
        self, client: TestClient, tom: User, applet_one_with_flow_update_data: AppletUpdate, applet_one: AppletFull
    ):
        client.login(tom)
        data = applet_one_with_flow_update_data.copy(deep=True)
        request_data = data.dict()
        request_data["activity_flows"].append(data.activity_flows[0].dict())
        resp = await client.put(self.applet_detail_url.format(pk=applet_one.id), data=request_data)
        assert resp.status_code == http.HTTPStatus.UNPROCESSABLE_ENTITY
        result = resp.json()["result"]
        assert len(result) == 1
        assert result[0]["message"] == DuplicateActivityFlowNameError.message

    async def test_update_applet__duplicate_flow_id(
        self, client: TestClient, tom: User, applet_one_with_flow_update_data: AppletUpdate, applet_one: AppletFull
    ):
        client.login(tom)
        data = applet_one_with_flow_update_data.copy(deep=True)
        flow = data.activity_flows[0].copy(deep=True)
        flow.name += "second"
        request_data = data.dict()
        request_data["activity_flows"].append(flow.dict())
        resp = await client.put(self.applet_detail_url.format(pk=applet_one.id), data=request_data)
        assert resp.status_code == http.HTTPStatus.UNPROCESSABLE_ENTITY
        result = resp.json()["result"]
        assert len(result) == 1
        assert result[0]["message"] == DuplicatedActivityFlowsError.message

    async def test_update_applet__flow_key_is_not_valid(
        self,
        client: TestClient,
        tom: User,
        applet_one_with_flow_update_data: AppletUpdate,
        applet_one: AppletFull,
        uuid_zero: uuid.UUID,
    ):
        client.login(tom)
        data = applet_one_with_flow_update_data.copy(deep=True)
        request_data = data.dict()
        request_data["activity_flows"][0]["items"][0]["activity_key"] = uuid_zero
        resp = await client.put(self.applet_detail_url.format(pk=applet_one.id), data=request_data)
        assert resp.status_code == http.HTTPStatus.BAD_REQUEST
        result = resp.json()["result"]
        assert len(result) == 1
        assert result[0]["message"] == FlowItemActivityKeyNotFoundError.message

    async def test_create_applet_with_flow(self, client: TestClient, tom: User, applet_create_with_flow: AppletCreate):
        client.login(tom)
        resp = await client.post(self.applet_create_url.format(owner_id=tom.id), data=applet_create_with_flow)
        assert resp.status_code == http.HTTPStatus.CREATED
        result = resp.json()["result"]
        assert len(result["activityFlows"]) == 1
        exp_flow = applet_create_with_flow.activity_flows[0]
        assert result["activityFlows"][0]["name"] == exp_flow.name
        assert result["activityFlows"][0]["description"] == exp_flow.description
        assert len(result["activityFlows"][0]["items"]) == 1
        assert result["activityFlows"][0]["items"][0]["activityId"] == result["activities"][0]["id"]

    async def test_create_applet_with_flow_auto_assign(
        self, client: TestClient, tom: User, applet_create_with_flow: AppletCreate
    ):
        client.login(tom)
        applet_create_with_flow.activity_flows[0].auto_assign = True
        resp = await client.post(self.applet_create_url.format(owner_id=tom.id), data=applet_create_with_flow)
        assert resp.status_code == http.HTTPStatus.CREATED
        result = resp.json()["result"]
        assert len(result["activityFlows"]) == 1
        assert result["activityFlows"][0]["autoAssign"] is True

    async def test_create_applet_without_flow_auto_assign(
        self, client: TestClient, tom: User, applet_create_with_flow: AppletCreate
    ):
        client.login(tom)
        applet_create_with_flow.activity_flows[0].auto_assign = False
        resp = await client.post(self.applet_create_url.format(owner_id=tom.id), data=applet_create_with_flow)
        assert resp.status_code == http.HTTPStatus.CREATED
        result = resp.json()["result"]
        assert len(result["activityFlows"]) == 1
        assert result["activityFlows"][0]["autoAssign"] is False

    async def test_update_applet_change_flow_auto_assign(
        self, client: TestClient, tom: User, applet_create_with_flow: AppletCreate
    ):
        client.login(tom)
        applet_create_with_flow.activity_flows[0].auto_assign = True
        createResp = await client.post(self.applet_create_url.format(owner_id=tom.id), data=applet_create_with_flow)
        assert createResp.status_code == http.HTTPStatus.CREATED
        createResult = createResp.json()["result"]

        update_data = AppletUpdate(
            display_name=applet_create_with_flow.display_name,
            activities=applet_create_with_flow.activities,
            activity_flows=applet_create_with_flow.activity_flows,
            encryption=applet_create_with_flow.encryption,
        )
        update_data.activities[0].id = createResult["activities"][0]["id"]
        update_data.activity_flows[0].id = createResult["activityFlows"][0]["id"]
        update_data.activity_flows[0].auto_assign = False
        updateResp = await client.put(
            self.applet_detail_url.format(pk=createResult["id"]),
            data=update_data,
        )
        assert updateResp.status_code == http.HTTPStatus.OK, updateResp.json()
        updateResult = updateResp.json()["result"]
        assert updateResult["activityFlows"][0]["autoAssign"] is False

    async def test_update_applet_delete_activity_with_assignments(
        self,
        client: TestClient,
        tom: User,
        applet_one_with_flow_and_assignments: AppletFull,
        applet_one_change_activities_ids: AppletUpdate,
        session: AsyncSession,
        tom_applet_one_subject,
    ):
        client.login(tom)

        assignment: ActivityAssigmentSchema | None = await ActivityAssigmentCRUD(session)._get(
            "activity_id", applet_one_with_flow_and_assignments.activities[0].id
        )
        assert assignment is not None
        assert assignment.soft_exists() is True

        updateResp = await client.put(
            self.applet_detail_url.format(pk=applet_one_with_flow_and_assignments.id),
            data=applet_one_change_activities_ids,
        )
        assert updateResp.status_code == http.HTTPStatus.OK, updateResp.json()

        assignment = await ActivityAssigmentCRUD(session)._get(
            "activity_id", applet_one_with_flow_and_assignments.activities[0].id
        )
        assert assignment is not None
        assert assignment.soft_exists() is False

    async def test_update_applet_delete_flow_with_assignments(
        self,
        client: TestClient,
        tom: User,
        applet_one_with_flow_and_assignments: AppletFull,
        applet_one_change_activities_ids: AppletUpdate,
        session: AsyncSession,
        tom_applet_one_subject,
    ):
        client.login(tom)

        assignment: ActivityAssigmentSchema | None = await ActivityAssigmentCRUD(session)._get(
            "activity_flow_id", applet_one_with_flow_and_assignments.activity_flows[0].id
        )
        assert assignment is not None
        assert assignment.soft_exists() is True

        updateResp = await client.put(
            self.applet_detail_url.format(pk=applet_one_with_flow_and_assignments.id),
            data=applet_one_change_activities_ids,
        )
        assert updateResp.status_code == http.HTTPStatus.OK, updateResp.json()

        assignment = await ActivityAssigmentCRUD(session)._get(
            "activity_flow_id", applet_one_with_flow_and_assignments.activity_flows[0].id
        )
        assert assignment is not None
        assert assignment.soft_exists() is False

    async def test_update_applet_keep_flow_auto_assign(
        self, client: TestClient, tom: User, applet_create_with_flow: AppletCreate
    ):
        client.login(tom)
        applet_create_with_flow.activity_flows[0].auto_assign = True
        createResp = await client.post(self.applet_create_url.format(owner_id=tom.id), data=applet_create_with_flow)
        assert createResp.status_code == http.HTTPStatus.CREATED
        createResult = createResp.json()["result"]

        update_data = AppletUpdate(
            display_name=applet_create_with_flow.display_name,
            activities=applet_create_with_flow.activities,
            activity_flows=applet_create_with_flow.activity_flows,
            encryption=applet_create_with_flow.encryption,
        )
        update_data.activities[0].id = createResult["activities"][0]["id"]
        update_data.activity_flows[0].id = createResult["activityFlows"][0]["id"]
        update_data.activity_flows[0].auto_assign = None
        updateResp = await client.put(
            self.applet_detail_url.format(pk=createResult["id"]),
            data=update_data,
        )
        assert updateResp.status_code == http.HTTPStatus.OK, updateResp.json()
        updateResult = updateResp.json()["result"]
        assert updateResult["activityFlows"][0]["autoAssign"] is True

    async def test_update_applet_activity_flow_report_config(
        self, client: TestClient, tom: User, applet_one_with_flow: AppletFull
    ):
        assert applet_one_with_flow.activity_flows[0].report_included_activity_name is None
        assert applet_one_with_flow.activity_flows[0].report_included_item_name is None
        client.login(tom)
        activity_name = applet_one_with_flow.activities[0].name
        item_name = applet_one_with_flow.activities[0].items[0].name
        resp = await client.put(
            self.flow_report_config_url.format(
                pk=applet_one_with_flow.id, flow_id=applet_one_with_flow.activity_flows[0].id
            ),
            data=dict(
                report_included_activity_name=activity_name,
                report_included_item_name=item_name,
            ),
        )
        assert resp.status_code == http.HTTPStatus.OK
        resp = await client.get(self.applet_detail_url.format(pk=applet_one_with_flow.id))
        assert resp.status_code == http.HTTPStatus.OK
        assert resp.json()["result"]["activityFlows"][0]["reportIncludedActivityName"] == activity_name
        assert resp.json()["result"]["activityFlows"][0]["reportIncludedItemName"] == item_name

    async def test_retrieve_applet_versions__applet_with_flow(
        self, client: TestClient, tom: User, applet_one_with_flow: AppletFull
    ):
        client.login(tom)
        resp = await client.get(
            self.history_url.format(pk=applet_one_with_flow.id, version=applet_one_with_flow.version)
        )
        assert resp.status_code == http.HTTPStatus.OK
        result = resp.json()["result"]
        # TODO: investigate why need the same values
        assert result["activityFlows"][0]["items"][0]["activity"] == result["activities"][0]
        flow_data = result["activityFlows"][0]
        exp_flow_data = applet_one_with_flow.activity_flows[0].dict(by_alias=True)
        assert flow_data["id"] == str(exp_flow_data["id"])
        assert flow_data["name"] == exp_flow_data["name"]
        assert flow_data["description"] == exp_flow_data["description"]
        assert flow_data["isSingleReport"] == exp_flow_data["isSingleReport"]
        assert flow_data["hideBadge"] == exp_flow_data["hideBadge"]
        assert flow_data["order"] == exp_flow_data["order"]

    @pytest.mark.usefixtures("applet_one_lucy_editor")
    async def test_create_applet__editor_create_applet__stil_editor_in_new_applet(
        self, client: TestClient, lucy: User, tom: User, applet_minimal_data: AppletCreate, mocker: MockerFixture
    ):
        client.login(lucy)
        mock = mocker.patch("apps.applets.service.AppletService._create_applet_accesses")
        resp = await client.post(self.applet_create_url.format(owner_id=tom.id), data=applet_minimal_data)
        assert resp.status_code == http.HTTPStatus.CREATED
        mock.assert_awaited_once_with(ANY, tom.id, lucy.id, Role.EDITOR)

    async def test_duplicate_applet__editor_duplicate_applet__stil_editor_in_new_applet(
        self,
        client: TestClient,
        lucy: User,
        tom: User,
        applet_one_lucy_editor: AppletFull,
        mocker: MockerFixture,
        encryption: Encryption,
    ):
        client.login(lucy)
        mock = mocker.patch("apps.applets.service.AppletService._create_applet_accesses")
        new_name = applet_one_lucy_editor.display_name + "new"
        resp = await client.post(
            self.applet_duplicate_url.format(pk=applet_one_lucy_editor.id),
            data=dict(display_name=new_name, encryption=encryption.dict()),
        )
        assert resp.status_code == http.HTTPStatus.CREATED
        mock.assert_awaited_once_with(ANY, tom.id, lucy.id, Role.EDITOR)

    async def test_get_applet_base_info_by_key__link_does_not_exist(
        self, client: TestClient, tom: User, uuid_zero: uuid.UUID
    ):
        client.login(tom)
        resp = await client.get(self.public_applet_base_info_url.format(key=uuid_zero))
        assert resp.status_code == http.HTTPStatus.NOT_FOUND

    async def test_update_applet_with_reviewable_activity__all_schedules_for_activity_are_deleted(
        self,
        client: TestClient,
        tom: User,
        applet_one: AppletFull,
        applet_one_update_data: AppletUpdate,
        mocker: MockerFixture,
    ):
        client.login(tom)
        data = applet_one_update_data.copy(deep=True)
        data.activities[0].is_reviewable = True
        mock = mocker.patch("apps.schedule.service.ScheduleService.delete_by_activity_ids")
        resp = await client.put(self.applet_detail_url.format(pk=applet_one.id), data=data)
        assert resp.status_code == http.HTTPStatus.OK
        mock.assert_awaited_once_with(applet_one.id, ANY)

    async def test_duplicate_applet__duplicate_applet_with_activity_flow(
        self, client: TestClient, tom: User, applet_one_with_flow: AppletFull, encryption: Encryption
    ):
        client.login(tom)
        new_name = applet_one_with_flow.display_name + "new"
        resp = await client.post(
            self.applet_duplicate_url.format(pk=applet_one_with_flow.id),
            data=dict(display_name=new_name, encryption=encryption.dict()),
        )
        assert resp.status_code == http.HTTPStatus.CREATED
        activity_flows = resp.json()["result"]["activityFlows"]
        assert len(activity_flows) == 1
        assert activity_flows[0]["name"] == applet_one_with_flow.activity_flows[0].name

    async def test_delete_applet_link__link_does_not_exists(
        self, client: TestClient, tom: User, applet_one: AppletFull
    ):
        client.login(tom)
        resp = await client.delete(self.access_link_url.format(pk=applet_one.id))
        assert resp.status_code == http.HTTPStatus.NOT_FOUND

    async def test_get_unique_name_for_applet__applet_name_with_number(
        self, client: TestClient, tom: User, applet_one: AppletFull, encryption: Encryption
    ):
        client.login(tom)
        new_name = AppletService.APPLET_NAME_FORMAT_FOR_DUPLICATES.format(applet_one.display_name, 1)
        resp = await client.post(
            self.applet_duplicate_url.format(pk=applet_one.id),
            data=dict(display_name=new_name, encryption=encryption.dict()),
        )
        assert resp.status_code == http.HTTPStatus.CREATED
        assert resp.json()["result"]["displayName"] == new_name

        resp = await client.post(self.applet_unique_name_url, data=dict(name=new_name))
        assert resp.status_code == http.HTTPStatus.OK
        assert resp.json()["result"]["name"] == AppletService.APPLET_NAME_FORMAT_FOR_DUPLICATES.format(new_name, 2)

    @pytest.mark.parametrize("not_valid_vesion", ("0", "00", "abc", "0.0", "None"))
    async def test_get_applet_changes__version_is_not_valid(
        self, client: TestClient, tom: User, applet_one: AppletFull, not_valid_vesion: str
    ):
        client.login(tom)
        resp = await client.get(self.history_changes_url.format(pk=applet_one.id, version=not_valid_vesion))
        assert resp.status_code == http.HTTPStatus.NOT_FOUND
        result = resp.json()["result"]
        assert len(result) == 1
        assert result[0]["message"] == AppletVersionNotFoundError.message

    async def test_get_applet_changes__one_applet_version(self, client: TestClient, tom: User, applet_one: AppletFull):
        client.login(tom)
        resp = await client.get(self.history_changes_url.format(pk=applet_one.id, version=applet_one.version))
        assert resp.status_code == http.HTTPStatus.OK
        assert resp.json()["result"]["displayName"] == f"New applet {applet_one.display_name} added"

    async def test_applet_retrieve_meta(
        self, client: TestClient, tom: User, applet_with_reviewable_activity: AppletFull
    ):
        client.login(tom)
        response = await client.get(self.applet_detail_url.format(pk=applet_with_reviewable_activity.id))
        assert response.status_code == http.HTTPStatus.OK
        assert response.json()["appletMeta"]["hasAssessment"]
