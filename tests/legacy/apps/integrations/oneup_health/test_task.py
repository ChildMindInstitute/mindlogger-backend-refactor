import re
import uuid
from unittest.mock import patch

import pytest
import respx

from apps.answers.crud.answers import AnswersEHRCRUD
from apps.answers.domain import EHRIngestionStatus
from apps.applets.domain.applet_full import AppletFull
from apps.integrations.oneup_health.service.task import task_ingest_user_data


# This code is dead.  Parts are left for future reference for mocking httpx2
class TestTaskIngestUserData:
    @pytest.mark.asyncio
    async def test_success(self, session, applet_one: AppletFull, httpx2_mock: respx.Router):
        # mock get user
        httpx2_mock.get(re.compile(".*/user-management/v1/user")).respond(
            json={
                "entry": [{"oneup_user_id": 1}],
                "success": True,
            }
        )

        # mock audit event
        httpx2_mock.get(
            re.compile(
                ".*/r4/AuditEvent\\?subtype=data-transfer-initiated%2Cmember-data-ingestion-completed%2Cmember-data-ingestion-timeout.*"
            )
        ).respond(
            json={
                "entry": [
                    {
                        "resource": {"id": "fakeid", "subtype": [{"code": "data-transfer-initiated"}]},
                    },
                    {
                        "resource": {"id": "fakeid", "subtype": [{"code": "member-data-ingestion-completed"}]},
                    },
                ],
                "total": 4,
            }
        )

        # mock patient resources
        httpx2_mock.get(re.compile(".*/r4/Patient")).respond(
            json={
                "total": 1,
                "entry": [
                    {
                        "fullUrl": "https://fake.url/r4/Patient/fakeid",
                        "resource": {"id": "health_provider_id_1"},
                    }
                ],
            }
        )

        with patch(
            "apps.integrations.oneup_health.service.ehr_storage.EHRStorage.upload_resources"
        ) as upload_resources:
            # Mock the storage to return a path
            upload_resources.return_value = "fake/storage/path", "fake_filename"

            with patch(
                "apps.integrations.oneup_health.service.ehr_storage.EHRStorage.upload_ehr_zip"
            ) as upload_ehr_zip:
                upload_ehr_zip.return_value = "fake_zip_filename", 100

                submit_id = uuid.uuid4()
                activity_id = applet_one.activities[0].id
                target_subject_id = uuid.uuid4()
                user_id = uuid.uuid4()
                task = await task_ingest_user_data.kicker().kiq(
                    target_subject_id=target_subject_id,
                    applet_id=applet_one.id,
                    submit_id=submit_id,
                    activity_id=activity_id,
                    user_id=user_id,
                )
                result = await task.wait_result()

                assert result.return_value == "fake/storage/path"
                assert upload_resources.called

                answers_ehr = await AnswersEHRCRUD(session).get_by_submit_id_and_activity_id(
                    submit_id=submit_id, activity_id=activity_id
                )
                assert answers_ehr is not None
                assert answers_ehr.ehr_storage_uri == "fake/storage/path"
                assert answers_ehr.ehr_ingestion_status == EHRIngestionStatus.COMPLETED
