import datetime
import json
import uuid
from typing import AsyncGenerator, cast

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.activities.domain.response_type_config import SingleSelectionConfig
from apps.activities.domain.response_values import SingleSelectionValues
from apps.activities.domain.scores_reports import ReportType, ScoresAndReports, Section
from apps.answers.db.schemas import AnswerSchema
from apps.applets.domain.applet_create_update import AppletCreate
from apps.applets.domain.applet_full import AppletFull
from apps.applets.domain.applet_link import CreateAccessLink
from apps.applets.domain.base import AppletReportConfigurationBase
from apps.applets.service.applet import AppletService
from apps.mailing.services import TestMail
from apps.shared.test import BaseTest
from apps.themes.service import ThemeService
from apps.users.domain import User
from infrastructure.utility import RedisCacheTest


@pytest.fixture
def section() -> Section:
    return Section(type=ReportType.section, name="testsection")


@pytest.fixture
def scores_and_reports(section: Section) -> ScoresAndReports:
    return ScoresAndReports(
        generate_report=True,
        show_score_summary=True,
        reports=[section],
    )


@pytest.fixture
def applet_report_configuration_data(
    user: User, tom: User, report_server_public_key: str
) -> AppletReportConfigurationBase:
    return AppletReportConfigurationBase(
        report_server_ip="localhost",
        report_public_key=report_server_public_key,
        report_recipients=[tom.email_encrypted, user.email_encrypted],
    )


@pytest.fixture
def applet_data(
    applet_minimal_data: AppletCreate,
    applet_report_configuration_data: AppletReportConfigurationBase,
    scores_and_reports: ScoresAndReports,
) -> AppletCreate:
    data = applet_minimal_data.copy(deep=True)
    data.display_name = "answers"
    data.activities[0].items[0].response_values = cast(
        SingleSelectionValues, data.activities[0].items[0].response_values
    )
    data.activities[0].items[0].config = cast(SingleSelectionConfig, data.activities[0].items[0].config)
    data.activities[0].items[0].response_values.options[0].alert = "alert"
    data.activities[0].items[0].config.set_alerts = True
    data.activities[0].scores_and_reports = scores_and_reports
    data.report_server_ip = applet_report_configuration_data.report_server_ip
    data.report_public_key = applet_report_configuration_data.report_public_key
    data.report_recipients = applet_report_configuration_data.report_recipients
    return AppletCreate(**data.dict())


@pytest.fixture
async def applet(session: AsyncSession, tom: User, applet_data: AppletCreate) -> AsyncGenerator[AppletFull, None]:
    srv = AppletService(session, tom.id)
    await ThemeService(session, tom.id).get_or_create_default()
    applet = await srv.create(applet_data)
    yield applet


@pytest.fixture
async def public_applet(session: AsyncSession, applet: AppletFull, tom: User) -> AppletFull:
    srv = AppletService(session, tom.id)
    await srv.create_access_link(applet.id, CreateAccessLink(require_login=False))
    applet = await srv.get_full_applet(applet.id)
    assert applet.link is not None
    return applet


@pytest.fixture
async def applet_with_reviewable_activity(
    session: AsyncSession, applet_minimal_data: AppletCreate, tom: User
) -> AppletFull:
    data = applet_minimal_data.copy(deep=True)
    data.display_name = "applet with reviewable activity"
    second_activity = data.activities[0].copy(deep=True)
    second_activity.name = data.activities[0].name + " review"
    data.activities.append(second_activity)
    data.activities[1].is_reviewable = True
    applet_create = AppletCreate(**data.dict())
    srv = AppletService(session, tom.id)
    applet = await srv.create(applet_create)
    return applet


class TestAnswerActivityItems(BaseTest):
    fixtures = [
        "workspaces/fixtures/workspaces.json",
    ]

    login_url = "/auth/login"
    answer_url = "/answers"
    public_answer_url = "/public/answers"

    review_activities_url = "/answers/applet/{applet_id}/review/activities"

    summary_activities_url = "/answers/applet/{applet_id}/summary/activities"
    identifiers_url = f"{summary_activities_url}/{{activity_id}}/identifiers"
    versions_url = f"{summary_activities_url}/{{activity_id}}/versions"

    answers_for_activity_url = "/answers/applet/{applet_id}/activities/{activity_id}/answers"
    applet_answers_export_url = "/answers/applet/{applet_id}/data"
    applet_answers_completions_url = "/answers/applet/{applet_id}/completions"
    applets_answers_completions_url = "/answers/applet/completions"
    applet_submit_dates_url = "/answers/applet/{applet_id}/dates"

    activity_answers_url = "/answers/applet/{applet_id}/answers/" "{answer_id}/activities/{activity_id}"
    assessment_answers_url = "/answers/applet/{applet_id}/answers/{answer_id}/assessment"

    answer_reviews_url = "/answers/applet/{applet_id}/answers/{answer_id}/reviews"  # noqa: E501
    answer_notes_url = "/answers/applet/{applet_id}/answers/{answer_id}/activities/{activity_id}/notes"  # noqa: E501
    answer_note_detail_url = "/answers/applet/{applet_id}/answers/{answer_id}/activities/{activity_id}/notes/{note_id}"  # noqa: E501
    latest_report_url = "/answers/applet/{applet_id}/activities/{activity_id}/answers/{respondent_id}/latest_report"  # noqa: E501

    async def test_answer_activity_items_create_for_respondent(self, mock_kiq_report, client, tom, applet: AppletFull):
        await client.login(self.login_url, tom.email_encrypted, "Test1234!")
        create_data = dict(
            submit_id=str(uuid.uuid4()),
            applet_id=str(applet.id),
            activity_id=str(applet.activities[0].id),
            version=applet.version,
            created_at=1690188731636,
            answer=dict(
                user_public_key="user key",
                answer=json.dumps(
                    dict(
                        value=str(uuid.uuid4()),
                        additional_text=None,
                    )
                ),
                events=json.dumps(dict(events=["event1", "event2"])),
                item_ids=[str(applet.activities[0].items[0].id)],
                identifier="encrypted_identifier",
                scheduled_time=1690188679657,
                start_time=1690188679657,
                end_time=1690188731636,
                scheduledEventId="eventId",
                localEndDate="2022-10-01",
                localEndTime="12:35:00",
            ),
            alerts=[
                dict(
                    activity_item_id=str(applet.activities[0].items[0].id),
                    message="hello world",
                )
            ],
            client=dict(
                appId="mindlogger-mobile",
                appVersion="0.21.48",
                width=819,
                height=1080,
            ),
        )

        response = await client.post(self.answer_url, data=create_data)
        assert response.status_code == 201, response.json()

        mock_kiq_report.assert_awaited_once()

        published_values = await RedisCacheTest().get(f"channel_{tom.id}")
        published_values = published_values or []
        assert len(published_values) == 1
        # 2 because alert for lucy and for tom
        assert len(RedisCacheTest()._storage) == 1
        assert len(TestMail.mails) == 1
        assert TestMail.mails[0].subject == "Response alert"
        # TODO: move to the fixtures with yield
        RedisCacheTest._storage = {}

    async def test_get_latest_summary(self, mock_report_server_response, mock_kiq_report, client, tom, applet):
        await client.login(self.login_url, tom.email_encrypted, "Test1234!")

        create_data = dict(
            submit_id=str(uuid.uuid4()),
            applet_id=str(applet.id),
            activity_id=str(applet.activities[0].id),
            version=applet.version,
            created_at=1690188731636,
            answer=dict(
                user_public_key="user key",
                answer=json.dumps(
                    dict(
                        value=str(uuid.uuid4()),
                        additional_text=None,
                    )
                ),
                events=json.dumps(dict(events=["event1", "event2"])),
                item_ids=[str(applet.activities[0].items[0].id)],
                identifier="encrypted_identifier",
                scheduled_time=1690188679657,
                start_time=1690188679657,
                end_time=1690188731636,
            ),
            client=dict(
                appId="mindlogger-mobile",
                appVersion="0.21.48",
                width=819,
                height=1080,
            ),
        )

        response = await client.post(self.answer_url, data=create_data)

        assert response.status_code == 201, response.json()
        response = await client.post(
            self.latest_report_url.format(
                applet_id=str(applet.id),
                activity_id=str(applet.activities[0].id),
                respondent_id=tom.id,
            ),
        )
        assert response.status_code == 200

    async def test_public_answer_activity_items_create_for_respondent(
        self, mock_kiq_report, client, tom, public_applet
    ):
        create_data = dict(
            submit_id=str(uuid.uuid4()),
            applet_id=str(public_applet.id),
            version=public_applet.version,
            activity_id=str(public_applet.activities[0].id),
            created_at=1690188731636,
            answer=dict(
                user_public_key="user key",
                events=json.dumps(dict(events=["event1", "event2"])),
                answer=json.dumps(
                    dict(
                        value=str(uuid.uuid4()),
                        additional_text=None,
                    )
                ),
                item_ids=[str(public_applet.activities[0].items[0].id)],
                scheduled_time=1690188679657,
                start_time=1690188679657,
                end_time=1690188731636,
            ),
            client=dict(
                appId="mindlogger-mobile",
                appVersion="0.21.48",
                width=819,
                height=1080,
            ),
        )

        response = await client.post(self.public_answer_url, data=create_data)

        assert response.status_code == 201, response.json()

    async def test_answer_skippable_activity_items_create_for_respondent(self, mock_kiq_report, client, tom, applet):
        await client.login(self.login_url, tom.email_encrypted, "Test1234!")

        create_data = dict(
            submit_id=str(uuid.uuid4()),
            applet_id=str(applet.id),
            activity_id=str(applet.activities[0].id),
            version=applet.version,
            answer=dict(
                start_time=1690188679657,
                end_time=1690188731636,
                itemIds=[str(applet.activities[0].items[0].id)],
            ),
            client=dict(
                appId="mindlogger-mobile",
                appVersion="0.21.48",
                width=819,
                height=1080,
            ),
        )

        response = await client.post(self.answer_url, data=create_data)

        assert response.status_code == 201, response.json()

        response = await client.get(
            self.applet_submit_dates_url.format(applet_id=str(applet.id)),
            dict(
                respondentId=tom.id,
                fromDate=datetime.date.today() - datetime.timedelta(days=10),
                toDate=datetime.date.today() + datetime.timedelta(days=10),
            ),
        )
        assert response.status_code == 200
        assert len(response.json()["result"]["dates"]) == 1

    async def test_list_submit_dates(self, mock_kiq_report, client, tom, applet):
        await client.login(self.login_url, tom.email_encrypted, "Test1234!")

        create_data = dict(
            submit_id=str(uuid.uuid4()),
            applet_id=str(applet.id),
            activity_id=str(applet.activities[0].id),
            version=applet.version,
            answer=dict(
                user_public_key="user key",
                events=json.dumps(dict(events=["event1", "event2"])),
                answer=json.dumps(
                    dict(
                        value=str(uuid.uuid4()),
                        additional_text=None,
                    )
                ),
                item_ids=[str(applet.activities[0].items[0].id)],
                scheduled_time=1690188679657,
                start_time=1690188679657,
                end_time=1690188731636,
            ),
            client=dict(
                appId="mindlogger-mobile",
                appVersion="0.21.48",
                width=819,
                height=1080,
            ),
        )

        response = await client.post(self.answer_url, data=create_data)
        assert response.status_code == 201, response.json()

        response = await client.get(
            self.applet_submit_dates_url.format(applet_id=str(applet.id)),
            dict(
                respondentId=tom.id,
                fromDate=datetime.date.today() - datetime.timedelta(days=10),
                toDate=datetime.date.today() + datetime.timedelta(days=10),
            ),
        )
        assert response.status_code == 200
        assert len(response.json()["result"]["dates"]) == 1

    async def test_answer_flow_items_create_for_respondent(self, mock_kiq_report, client, tom, applet):
        await client.login(self.login_url, tom.email_encrypted, "Test1234!")

        create_data = dict(
            submit_id=str(uuid.uuid4()),
            applet_id=str(applet.id),
            version=applet.version,
            created_at=1690188731636,
            flow_id="3013dfb1-9202-4577-80f2-ba7450fb5831",
            activity_id=str(applet.activities[0].id),
            answer=dict(
                user_public_key="user key",
                events=json.dumps(dict(events=["event1", "event2"])),
                answer=json.dumps(
                    dict(
                        value=str(uuid.uuid4()),
                        additional_text=None,
                    )
                ),
                item_ids=[str(applet.activities[0].items[0].id)],
                scheduled_time=1690188679657,
                start_time=1690188679657,
                end_time=1690188731636,
            ),
            client=dict(
                appId="mindlogger-mobile",
                appVersion="0.21.48",
                width=819,
                height=1080,
            ),
        )

        response = await client.post(self.answer_url, data=create_data)

        assert response.status_code == 201, response.json()

    async def test_answer_with_skipping_all(self, mock_kiq_report, client, tom, applet):
        await client.login(self.login_url, tom.email_encrypted, "Test1234!")

        create_data = dict(
            submit_id=str(uuid.uuid4()),
            applet_id=str(applet.id),
            activity_id=str(applet.activities[0].id),
            version=applet.version,
            created_at=1690188731636,
            answer=dict(
                start_time=1690188679657,
                end_time=1690188731636,
                itemIds=[str(applet.activities[0].items[0].id)],
            ),
            client=dict(
                appId="mindlogger-mobile",
                appVersion="0.21.48",
                width=819,
                height=1080,
            ),
        )

        response = await client.post(self.answer_url, data=create_data)

        assert response.status_code == 201, response.json()

    async def test_answered_applet_activities(self, mock_kiq_report, client, tom, applet):
        await client.login(self.login_url, tom.email_encrypted, "Test1234!")

        create_data = dict(
            submit_id=str(uuid.uuid4()),
            applet_id=str(applet.id),
            version=applet.version,
            activity_id=str(applet.activities[0].id),
            answer=dict(
                user_public_key="user key",
                events=json.dumps(dict(events=["event1", "event2"])),
                answer=json.dumps(
                    dict(
                        value=str(uuid.uuid4()),
                        additional_text=None,
                    )
                ),
                item_ids=[str(applet.activities[0].items[0].id)],
                scheduled_time=1690188679657,
                start_time=1690188679657,
                end_time=1690188731636,
            ),
            client=dict(
                appId="mindlogger-mobile",
                appVersion="0.21.48",
                width=819,
                height=1080,
            ),
        )

        response = await client.post(self.answer_url, data=create_data)

        assert response.status_code == 201, response.json()

        response = await client.get(
            self.review_activities_url.format(applet_id=str(applet.id)),
            dict(
                respondentId=tom.id,
                createdDate=datetime.datetime.utcnow().date(),
            ),
        )

        assert response.status_code == 200, response.json()
        assert response.json()["count"] == 1
        assert len(response.json()["result"][0]["answerDates"]) == 1

        answer_id = response.json()["result"][0]["answerDates"][0]["answerId"]
        response = await client.get(
            self.activity_answers_url.format(
                applet_id=str(applet.id),
                answer_id=answer_id,
                activity_id=str(applet.activities[0].id),
            )
        )

        assert response.status_code == 200, response.json()

        response = await client.get(
            self.activity_answers_url.format(
                applet_id=str(applet.id),
                answer_id=answer_id,
                activity_id=str(applet.activities[0].id),
            )
        )

        assert response.status_code == 200, response.json()
        assert response.json()["result"]["events"] == '{"events": ["event1", "event2"]}'

    async def test_fail_answered_applet_not_existed_activities(self, mock_kiq_report, client, tom, applet):
        await client.login(self.login_url, tom.email_encrypted, "Test1234!")

        create_data = dict(
            submit_id=str(uuid.uuid4()),
            applet_id=str(applet.id),
            version=applet.version,
            activity_id=str(applet.activities[0].id),
            answer=dict(
                user_public_key="user key",
                events=json.dumps(dict(events=["event1", "event2"])),
                answer=json.dumps(
                    dict(
                        value=str(uuid.uuid4()),
                        additional_text=None,
                    )
                ),
                item_ids=[str(applet.activities[0].items[0].id)],
                scheduled_time=1690188679657,
                start_time=1690188679657,
                end_time=1690188731636,
            ),
            client=dict(
                appId="mindlogger-mobile",
                appVersion="0.21.48",
                width=819,
                height=1080,
            ),
        )

        response = await client.post(self.answer_url, data=create_data)

        assert response.status_code == 201, response.json()

        response = await client.get(
            self.review_activities_url.format(applet_id=str(applet.id)),
            dict(
                respondentId=tom.id,
                createdDate=datetime.datetime.utcnow().date(),
            ),
        )

        assert response.status_code == 200, response.json()
        assert response.json()["count"] == 1
        assert len(response.json()["result"][0]["answerDates"]) == 1

        answer_id = response.json()["result"][0]["answerDates"][0]["answerId"]
        response = await client.get(
            self.activity_answers_url.format(
                applet_id=str(applet.id),
                answer_id=answer_id,
                activity_id="00000000-0000-0000-0000-000000000000",
            )
        )

        assert response.status_code == 404, response.json()

    async def test_applet_activity_answers(self, mock_kiq_report, client, tom, applet):
        await client.login(self.login_url, tom.email_encrypted, "Test1234!")

        create_data = dict(
            submit_id=str(uuid.uuid4()),
            applet_id=str(applet.id),
            version=applet.version,
            activity_id=str(applet.activities[0].id),
            answer=dict(
                user_public_key="user key",
                events=json.dumps(dict(events=["event1", "event2"])),
                answer=json.dumps(
                    dict(
                        value=str(uuid.uuid4()),
                        additional_text=None,
                    )
                ),
                item_ids=[str(applet.activities[0].items[0].id)],
                scheduled_time=1690188679657,
                start_time=1690188679657,
                end_time=1690188731636,
            ),
            client=dict(
                appId="mindlogger-mobile",
                appVersion="0.21.48",
                width=819,
                height=1080,
            ),
        )

        response = await client.post(self.answer_url, data=create_data)

        assert response.status_code == 201, response.json()

        response = await client.get(
            self.answers_for_activity_url.format(
                applet_id=str(applet.id),
                activity_id=str(applet.activities[0].id),
            ),
        )

        assert response.status_code == 200, response.json()
        assert response.json()["count"] == 1

    async def test_applet_assessment_retrieve(self, mock_kiq_report, client, tom, applet):
        await client.login(self.login_url, tom.email_encrypted, "Test1234!")

        create_data = dict(
            submit_id=str(uuid.uuid4()),
            applet_id=str(applet.id),
            version=applet.version,
            activity_id=str(applet.activities[0].id),
            answer=dict(
                user_public_key="user key",
                answer=json.dumps(
                    dict(
                        value=str(uuid.uuid4()),
                        additional_text=None,
                    )
                ),
                item_ids=[str(applet.activities[0].items[0].id)],
                scheduled_time=1690188679657,
                start_time=1690188679657,
                end_time=1690188731636,
            ),
            client=dict(
                appId="mindlogger-mobile",
                appVersion="0.21.48",
                width=819,
                height=1080,
            ),
        )

        response = await client.post(self.answer_url, data=create_data)

        assert response.status_code == 201, response.json()

        response = await client.get(
            self.review_activities_url.format(applet_id=str(applet.id)),
            dict(
                respondentId=tom.id,
                createdDate=datetime.datetime.utcnow().date(),
            ),
        )

        assert response.status_code == 200, response.json()
        assert response.json()["count"] == 1
        assert len(response.json()["result"][0]["answerDates"]) == 1

        answer_id = response.json()["result"][0]["answerDates"][0]["answerId"]
        response = await client.get(
            self.assessment_answers_url.format(
                applet_id=str(applet.id),
                answer_id=answer_id,
            )
        )

        assert response.status_code == 200, response.json()

    async def test_applet_assessment_create(self, mock_kiq_report, client, tom, applet_with_reviewable_activity):
        await client.login(self.login_url, tom.email_encrypted, "Test1234!")

        create_data = dict(
            submit_id=str(uuid.uuid4()),
            applet_id=str(applet_with_reviewable_activity.id),
            version=applet_with_reviewable_activity.version,
            activity_id=str(applet_with_reviewable_activity.activities[0].id),
            answer=dict(
                user_public_key="user key",
                answer=json.dumps(
                    dict(
                        value=str(uuid.uuid4()),
                        additional_text=None,
                    )
                ),
                item_ids=[str(applet_with_reviewable_activity.activities[0].items[0].id)],
                scheduled_time=1690188679657,
                start_time=1690188679657,
                end_time=1690188731636,
            ),
            client=dict(
                appId="mindlogger-mobile",
                appVersion="0.21.48",
                width=819,
                height=1080,
            ),
        )

        response = await client.post(self.answer_url, data=create_data)

        assert response.status_code == 201, response.json()

        response = await client.get(
            self.review_activities_url.format(applet_id=str(applet_with_reviewable_activity.id)),
            dict(
                respondentId=tom.id,
                createdDate=datetime.datetime.utcnow().date(),
            ),
        )

        assert response.status_code == 200, response.json()
        assert response.json()["count"] == 1
        assert len(response.json()["result"][0]["answerDates"]) == 1

        answer_id = response.json()["result"][0]["answerDates"][0]["answerId"]

        # create assessment
        response = await client.post(
            self.assessment_answers_url.format(
                applet_id=str(applet_with_reviewable_activity.id),
                answer_id=answer_id,
            ),
            dict(
                answer="some answer",
                item_ids=[str(applet_with_reviewable_activity.activities[0].items[0].id)],
                reviewer_public_key="some public key",
                assessment_version_id=(
                    f"{applet_with_reviewable_activity.activities[0].id}_{applet_with_reviewable_activity.version}"
                ),
            ),
        )

        assert response.status_code == 201

        response = await client.get(
            self.assessment_answers_url.format(
                applet_id=str(applet_with_reviewable_activity.id),
                answer_id=answer_id,
            )
        )

        assert response.status_code == 200, response.json()
        assert response.json()["result"]["answer"] == "some answer"
        assert response.json()["result"]["reviewerPublicKey"] == "some public key"
        assert response.json()["result"]["itemIds"] == [str(applet_with_reviewable_activity.activities[0].items[0].id)]

        response = await client.post(
            self.assessment_answers_url.format(
                applet_id=str(applet_with_reviewable_activity.id),
                answer_id=answer_id,
            ),
            dict(
                answer="some answer",
                item_ids=[str(applet_with_reviewable_activity.activities[0].items[0].id)],
                reviewer_public_key="some public key",
                assessment_version_id=(
                    f"{applet_with_reviewable_activity.activities[0].id}_{applet_with_reviewable_activity.version}"
                ),
            ),
        )

        assert response.status_code == 201

        response = await client.get(
            self.assessment_answers_url.format(
                applet_id=str(applet_with_reviewable_activity.id),
                answer_id=answer_id,
            )
        )

        assert response.status_code == 200, response.json()
        assert response.json()["result"]["answer"] == "some answer"
        assert response.json()["result"]["reviewerPublicKey"] == "some public key"
        assert response.json()["result"]["itemIds"] == [str(applet_with_reviewable_activity.activities[0].items[0].id)]
        response = await client.get(
            self.answer_reviews_url.format(
                applet_id=str(applet_with_reviewable_activity.id),
                answer_id=answer_id,
            )
        )

        assert response.status_code == 200, response.json()
        assert response.json()["count"] == 1
        assert response.json()["result"][0]["answer"] == "some answer"
        assert response.json()["result"][0]["reviewerPublicKey"] == "some public key"
        assert response.json()["result"][0]["itemIds"] == [
            str(applet_with_reviewable_activity.activities[0].items[0].id)
        ]
        assert response.json()["result"][0]["reviewer"]["firstName"] == "Tom"
        assert response.json()["result"][0]["reviewer"]["lastName"] == "Isaak"

    async def test_applet_activities(self, mock_kiq_report, client, tom, applet):
        await client.login(self.login_url, tom.email_encrypted, "Test1234!")

        response = await client.get(
            self.review_activities_url.format(applet_id=str(applet.id)),
            dict(
                respondentId=tom.id,
                createdDate=datetime.datetime.utcnow().date(),
            ),
        )

        assert response.status_code == 200, response.json()
        assert response.json()["count"] == 1
        assert len(response.json()["result"][0]["answerDates"]) == 0

    async def test_add_note(self, mock_kiq_report, client, tom, applet):
        await client.login(self.login_url, tom.email_encrypted, "Test1234!")

        create_data = dict(
            submit_id=str(uuid.uuid4()),
            applet_id=str(applet.id),
            version=applet.version,
            activity_id=str(applet.activities[0].id),
            answer=dict(
                user_public_key="user key",
                answer=json.dumps(
                    dict(
                        value=str(uuid.uuid4()),
                        additional_text=None,
                    )
                ),
                item_ids=[str(applet.activities[0].items[0].id)],
                scheduled_time=1690188679657,
                start_time=1690188679657,
                end_time=1690188731636,
            ),
            client=dict(
                appId="mindlogger-mobile",
                appVersion="0.21.48",
                width=819,
                height=1080,
            ),
        )

        response = await client.post(self.answer_url, data=create_data)

        assert response.status_code == 201, response.json()

        response = await client.get(
            self.review_activities_url.format(applet_id=str(applet.id)),
            dict(
                respondentId=tom.id,
                createdDate=datetime.datetime.utcnow().date(),
            ),
        )
        answer_id = response.json()["result"][0]["answerDates"][0]["answerId"]

        response = await client.post(
            self.answer_notes_url.format(
                applet_id=str(applet.id),
                answer_id=answer_id,
                activity_id=str(applet.activities[0].id),
            ),
            dict(note="Some note"),
        )

        assert response.status_code == 201, response.json()

        response = await client.get(
            self.answer_notes_url.format(
                applet_id=str(applet.id),
                answer_id=answer_id,
                activity_id=str(applet.activities[0].id),
            ),
        )

        assert response.status_code == 200, response.json()
        assert response.json()["count"] == 1

    async def test_edit_note(self, mock_kiq_report, client, tom, applet):
        await client.login(self.login_url, tom.email_encrypted, "Test1234!")

        create_data = dict(
            submit_id=str(uuid.uuid4()),
            applet_id=str(applet.id),
            version=applet.version,
            activity_id=str(applet.activities[0].id),
            answer=dict(
                user_public_key="user key",
                answer=json.dumps(
                    dict(
                        value=str(uuid.uuid4()),
                        additional_text=None,
                    )
                ),
                item_ids=[str(applet.activities[0].items[0].id)],
                scheduled_time=1690188679657,
                start_time=1690188679657,
                end_time=1690188731636,
            ),
            client=dict(
                appId="mindlogger-mobile",
                appVersion="0.21.48",
                width=819,
                height=1080,
            ),
        )

        response = await client.post(self.answer_url, data=create_data)

        assert response.status_code == 201, response.json()

        response = await client.get(
            self.review_activities_url.format(applet_id=str(applet.id)),
            dict(
                respondentId=tom.id,
                createdDate=datetime.datetime.utcnow().date(),
            ),
        )
        answer_id = response.json()["result"][0]["answerDates"][0]["answerId"]

        response = await client.post(
            self.answer_notes_url.format(
                applet_id=str(applet.id),
                answer_id=answer_id,
                activity_id=str(applet.activities[0].id),
            ),
            dict(note="Some note"),
        )

        assert response.status_code == 201, response.json()

        response = await client.get(
            self.answer_notes_url.format(
                applet_id=str(applet.id),
                answer_id=answer_id,
                activity_id=str(applet.activities[0].id),
            ),
        )

        assert response.status_code == 200, response.json()
        assert response.json()["count"] == 1
        assert response.json()["result"][0]["note"] == "Some note"

        response = await client.put(
            self.answer_note_detail_url.format(
                applet_id=str(applet.id),
                answer_id=answer_id,
                activity_id=str(applet.activities[0].id),
                note_id=response.json()["result"][0]["id"],
            ),
            dict(note="Some note 2"),
        )
        assert response.status_code == 200

        response = await client.get(
            self.answer_notes_url.format(
                applet_id=str(applet.id),
                answer_id=answer_id,
                activity_id=str(applet.activities[0].id),
            ),
        )

        assert response.status_code == 200, response.json()
        assert response.json()["count"] == 1
        assert response.json()["result"][0]["note"] == "Some note 2"

    async def test_delete_note(self, mock_kiq_report, client, tom, applet):
        await client.login(self.login_url, tom.email_encrypted, "Test1234!")

        create_data = dict(
            submit_id=str(uuid.uuid4()),
            applet_id=str(applet.id),
            version=applet.version,
            activity_id=str(applet.activities[0].id),
            answer=dict(
                user_public_key="user key",
                answer=json.dumps(
                    dict(
                        value=str(uuid.uuid4()),
                        additional_text=None,
                    )
                ),
                item_ids=[str(applet.activities[0].items[0].id)],
                scheduled_time=None,
                start_time=1690188679657,
                end_time=1690188731636,
            ),
            client=dict(
                appId="mindlogger-mobile",
                appVersion="0.21.48",
                width=819,
                height=1080,
            ),
        )

        response = await client.post(self.answer_url, data=create_data)

        assert response.status_code == 201, response.json()

        response = await client.get(
            self.review_activities_url.format(applet_id=str(applet.id)),
            dict(
                respondentId=tom.id,
                createdDate=datetime.datetime.utcnow().date(),
            ),
        )
        answer_id = response.json()["result"][0]["answerDates"][0]["answerId"]

        response = await client.post(
            self.answer_notes_url.format(
                applet_id=str(applet.id),
                answer_id=answer_id,
                activity_id=str(applet.activities[0].id),
            ),
            dict(note="Some note"),
        )

        assert response.status_code == 201, response.json()

        response = await client.get(
            self.answer_notes_url.format(
                applet_id=str(applet.id),
                answer_id=answer_id,
                activity_id=str(applet.activities[0].id),
            ),
        )

        assert response.status_code == 200, response.json()
        assert response.json()["count"] == 1
        assert response.json()["result"][0]["note"] == "Some note"

        response = await client.delete(
            self.answer_note_detail_url.format(
                applet_id=str(applet.id),
                answer_id=answer_id,
                activity_id=str(applet.activities[0].id),
                note_id=response.json()["result"][0]["id"],
            )
        )
        assert response.status_code == 204

        response = await client.get(
            self.answer_notes_url.format(
                applet_id=str(applet.id),
                answer_id=answer_id,
                activity_id=str(applet.activities[0].id),
            ),
        )

        assert response.status_code == 200, response.json()
        assert response.json()["count"] == 0

    @pytest.mark.usefixtures("mock_kiq_report", "user")
    async def test_answer_activity_items_create_for_not_respondent(self, client, applet):
        await client.login(self.login_url, "user@example.com", "Test1234!")

        create_data = dict(
            submit_id=str(uuid.uuid4()),
            applet_id=str(applet.id),
            version=applet.version,
            activity_id=str(applet.activities[0].id),
            answer=dict(
                user_public_key="user key",
                answer=json.dumps(
                    dict(
                        value=str(uuid.uuid4()),
                    )
                ),
                item_ids=[str(applet.activities[0].items[0].id)],
                scheduled_time=1690188679657,
                start_time=1690188679657,
                end_time=1690188731636,
            ),
            client=dict(
                appId="mindlogger-mobile",
                appVersion="0.21.48",
                width=819,
                height=1080,
            ),
        )

        response = await client.post(self.answer_url, data=create_data)

        assert response.status_code == 403, response.json()

    async def test_answers_export(self, mock_kiq_report, client, tom, applet):
        await client.login(self.login_url, tom.email_encrypted, "Test1234!")

        # create answer
        create_data = dict(
            submit_id=str(uuid.uuid4()),
            applet_id=str(applet.id),
            version=applet.version,
            activity_id=str(applet.activities[0].id),
            answer=dict(
                user_public_key="user key",
                answer=json.dumps(
                    dict(
                        value=str(uuid.uuid4()),
                        additional_text=None,
                    )
                ),
                item_ids=[str(applet.activities[0].items[0].id)],
                scheduled_time=1690188679657,
                start_time=1690188679657,
                end_time=1690188731636,
            ),
            client=dict(
                appId="mindlogger-mobile",
                appVersion="0.21.48",
                width=819,
                height=1080,
            ),
        )

        response = await client.post(self.answer_url, data=create_data)

        assert response.status_code == 201

        # get answer id
        response = await client.get(
            self.review_activities_url.format(applet_id=str(applet.id)),
            dict(
                respondentId=tom.id,
                createdDate=datetime.datetime.utcnow().date(),
            ),
        )

        assert response.status_code == 200, response.json()
        answer_id = response.json()["result"][0]["answerDates"][0]["answerId"]

        # create assessment
        response = await client.post(
            self.assessment_answers_url.format(
                applet_id=str(applet.id),
                answer_id=answer_id,
            ),
            dict(
                answer="some answer",
                item_ids=["a18d3409-2c96-4a5e-a1f3-1c1c14be0021"],
                reviewer_public_key="some public key",
                assessment_version_id=("09e3dbf0-aefb-4d0e-9177-bdb321bf3621_1.0.0"),
            ),
        )

        assert response.status_code == 201

        # test export
        response = await client.get(
            self.applet_answers_export_url.format(
                applet_id=str(applet.id),
            )
        )

        assert response.status_code == 200, response.json()
        resp_data = response.json()
        data = resp_data["result"]
        assert set(data.keys()) == {"answers", "activities"}
        assert len(data["answers"]) == 2
        assert resp_data["count"] == 2

        assessment, answer = data["answers"][0], data["answers"][1]
        # fmt: off
        expected_keys = {
            "activityHistoryId", "activityId", "answer", "appletHistoryId",
            "appletId", "createdAt", "events", "flowHistoryId", "flowId",
            "flowName", "id", "itemIds", "migratedData", "respondentId",
            "respondentSecretId", "reviewedAnswerId", "userPublicKey",
            "version", "submitId", "scheduledDatetime", "startDatetime",
            "endDatetime", "legacyProfileId", "migratedDate", "client",
        }
        assert int(answer['startDatetime'] * 1000) == 1690188679657
        # fmt: on

        assert set(assessment.keys()) == expected_keys
        assert assessment["reviewedAnswerId"] == answer["id"]

        # test filters
        response = await client.get(
            self.applet_answers_export_url.format(
                applet_id=str(applet.id),
            ),
            dict(
                respondentIds="7484f34a-3acc-4ee6-8a94-000000000000",
            ),
        )

        assert response.status_code == 200, response.json()
        data = response.json()["result"]
        assert not data["answers"]

    async def test_get_identifiers(self, mock_kiq_report, client, tom, applet):
        await client.login(self.login_url, tom.email_encrypted, "Test1234!")

        response = await client.get(
            self.identifiers_url.format(
                applet_id=str(applet.id),
                activity_id=str(applet.activities[0].id),
            )
        )

        assert response.status_code == 200
        assert response.json()["count"] == 0

        create_data = dict(
            submit_id=str(uuid.uuid4()),
            applet_id=str(applet.id),
            version=applet.version,
            activity_id=str(applet.activities[0].id),
            answer=dict(
                user_public_key="user key",
                answer=json.dumps(
                    dict(
                        value=str(uuid.uuid4()),
                        additional_text=None,
                    )
                ),
                item_ids=[str(applet.activities[0].items[0].id)],
                identifier="some identifier",
                scheduled_time=1690188679657,
                start_time=1690188679657,
                end_time=1690188731636,
            ),
            client=dict(
                appId="mindlogger-mobile",
                appVersion="0.21.48",
                width=819,
                height=1080,
            ),
        )

        response = await client.post(self.answer_url, data=create_data)

        assert response.status_code == 201, response.json()

        response = await client.get(
            self.identifiers_url.format(
                applet_id=str(applet.id),
                activity_id=str(applet.activities[0].id),
            )
        )

        assert response.status_code == 200
        assert response.json()["count"] == 1
        assert response.json()["result"][0]["identifier"] == "some identifier"
        assert response.json()["result"][0]["userPublicKey"] == "user key"

    async def test_get_versions(self, mock_kiq_report, client, tom, applet):
        await client.login(self.login_url, tom.email_encrypted, "Test1234!")

        response = await client.get(
            self.versions_url.format(
                applet_id=str(applet.id),
                activity_id=str(applet.activities[0].id),
            )
        )

        assert response.status_code == 200
        assert response.json()["count"] == 1
        assert response.json()["result"][0]["version"] == applet.version
        assert response.json()["result"][0]["createdAt"]

    async def test_get_summary_activities(self, mock_kiq_report, client, tom, applet):
        await client.login(self.login_url, tom.email_encrypted, "Test1234!")

        response = await client.get(
            self.summary_activities_url.format(
                applet_id=str(applet.id),
            )
        )

        assert response.status_code == 200
        assert response.json()["count"] == 1
        assert response.json()["result"][0]["name"] == applet.activities[0].name
        assert not response.json()["result"][0]["isPerformanceTask"]
        assert not response.json()["result"][0]["hasAnswer"]

    async def test_get_summary_activities_after_submitted_answer(self, mock_kiq_report, client, tom, applet):
        await client.login(self.login_url, tom.email_encrypted, "Test1234!")

        create_data = dict(
            submit_id=str(uuid.uuid4()),
            applet_id=str(applet.id),
            version=applet.version,
            activity_id=str(applet.activities[0].id),
            answer=dict(
                user_public_key="user key",
                answer=json.dumps(
                    dict(
                        value=str(uuid.uuid4()),
                        additional_text=None,
                    )
                ),
                item_ids=[str(applet.activities[0].items[0].id)],
                identifier="some identifier",
                scheduled_time=1690188679657,
                start_time=1690188679657,
                end_time=1690188731636,
            ),
            client=dict(
                appId="mindlogger-mobile",
                appVersion="0.21.48",
                width=819,
                height=1080,
            ),
        )

        response = await client.post(self.answer_url, data=create_data)
        assert response.status_code == 201

        response = await client.get(
            self.summary_activities_url.format(
                applet_id=str(applet.id),
            )
        )

        assert response.status_code == 200
        assert response.json()["count"] == 1
        assert response.json()["result"][0]["hasAnswer"]

    async def test_store_client_meta(self, mock_kiq_report, client, session, tom, applet):
        app_id = "mindlogger-mobile"
        app_version = "0.21.48"
        app_width = 819
        app_height = 1080

        await client.login(self.login_url, tom.email_encrypted, "Test1234!")
        create_data = dict(
            submit_id=str(uuid.uuid4()),
            applet_id=str(applet.id),
            version=applet.version,
            activity_id=str(applet.activities[0].id),
            answer=dict(
                user_public_key="user key",
                answer=json.dumps(
                    dict(
                        value=str(uuid.uuid4()),
                        additional_text=None,
                    )
                ),
                item_ids=[str(applet.activities[0].items[0].id)],
                identifier="some identifier",
                scheduled_time=10,
                start_time=10,
                end_time=11,
            ),
            client=dict(
                appId=app_id,
                appVersion=app_version,
                width=app_width,
                height=app_height,
            ),
        )
        response = await client.post(self.answer_url, data=create_data)
        assert response.status_code == 201
        db_result = await session.execute(select(AnswerSchema))
        res: AnswerSchema = db_result.scalars().first()
        assert app_id == res.client["app_id"]
        assert app_version == res.client["app_version"]
        assert app_width == res.client["width"]
        assert app_height == res.client["height"]

    async def test_activity_answers_by_identifier(self, mock_kiq_report, client, tom, applet):
        await client.login(self.login_url, tom.email_encrypted, "Test1234!")

        create_data = dict(
            submit_id=str(uuid.uuid4()),
            applet_id=str(applet.id),
            version=applet.version,
            activity_id=str(applet.activities[0].id),
            answer=dict(
                user_public_key="user key",
                events=json.dumps(dict(events=["event1", "event2"])),
                answer=json.dumps(
                    dict(
                        value=str(uuid.uuid4()),
                        additional_text=None,
                    )
                ),
                item_ids=[str(applet.activities[0].items[0].id)],
                scheduled_time=1690188679657,
                start_time=1690188679657,
                end_time=1690188731636,
                identifier="encrypted",
            ),
            client=dict(
                appId="mindlogger-mobile",
                appVersion="0.21.48",
                width=819,
                height=1080,
            ),
        )

        response = await client.post(self.answer_url, data=create_data)

        assert response.status_code == 201, response.json()

        response = await client.get(
            self.answers_for_activity_url.format(
                applet_id=str(applet.id),
                activity_id=str(applet.activities[0].id),
            ),
            query={"emptyIdentifiers": False, "identifiers": "encrypted"},
        )

        assert response.status_code == 200, response.json()
        result = response.json()
        assert result["count"] == 1

    async def test_applet_completions(self, mock_kiq_report, client, tom, applet):
        await client.login(self.login_url, tom.email_encrypted, "Test1234!")

        # create answer
        create_data = dict(
            submit_id=str(uuid.uuid4()),
            applet_id=str(applet.id),
            version=applet.version,
            activity_id=str(applet.activities[0].id),
            answer=dict(
                user_public_key="user key",
                answer=json.dumps(
                    dict(
                        value=str(uuid.uuid4()),
                        additional_text=None,
                    )
                ),
                item_ids=[str(applet.activities[0].items[0].id)],
                scheduled_time=1690188679657,
                start_time=1690188679657,
                end_time=1690188731636,
                scheduledEventId="eventId",
                localEndDate="2022-10-01",
                localEndTime="12:35:00",
            ),
            client=dict(
                appId="mindlogger-mobile",
                appVersion="0.21.48",
                width=819,
                height=1080,
            ),
        )

        response = await client.post(self.answer_url, data=create_data)

        assert response.status_code == 201

        # get answer id
        response = await client.get(
            self.review_activities_url.format(applet_id=str(applet.id)),
            dict(
                respondentId=tom.id,
                createdDate=datetime.datetime.utcnow().date(),
            ),
        )

        assert response.status_code == 200, response.json()
        answer_id = response.json()["result"][0]["answerDates"][0]["answerId"]

        # test completions
        response = await client.get(
            self.applet_answers_completions_url.format(
                applet_id=str(applet.id),
            ),
            {"fromDate": "2022-10-01", "version": applet.version},
        )

        assert response.status_code == 200, response.json()
        data = response.json()["result"]
        assert set(data.keys()) == {
            "id",
            "version",
            "activities",
            "activityFlows",
        }
        assert len(data["activities"]) == 1
        activity_answer_data = data["activities"][0]
        assert set(activity_answer_data.keys()) == {
            "id",
            "answerId",
            "submitId",
            "scheduledEventId",
            "localEndDate",
            "localEndTime",
        }
        assert activity_answer_data["answerId"] == answer_id
        assert activity_answer_data["localEndTime"] == "12:35:00"

    async def test_applets_completions(self, mock_kiq_report, client, tom, applet):
        await client.login(self.login_url, tom.email_encrypted, "Test1234!")

        # create answer
        create_data = dict(
            submit_id=str(uuid.uuid4()),
            applet_id=str(applet.id),
            version=applet.version,
            activity_id=str(applet.activities[0].id),
            answer=dict(
                user_public_key="user key",
                answer=json.dumps(
                    dict(
                        value=str(uuid.uuid4()),
                        additional_text=None,
                    )
                ),
                item_ids=[str(applet.activities[0].items[0].id)],
                scheduled_time=1690188679657,
                start_time=1690188679657,
                end_time=1690188731636,
                scheduledEventId="eventId",
                localEndDate="2022-10-01",
                localEndTime="12:35:00",
            ),
            client=dict(
                appId="mindlogger-mobile",
                appVersion="0.21.48",
                width=819,
                height=1080,
            ),
        )

        response = await client.post(self.answer_url, data=create_data)

        assert response.status_code == 201

        # get answer id
        response = await client.get(
            self.review_activities_url.format(applet_id=str(applet.id)),
            dict(
                respondentId=tom.id,
                createdDate=datetime.datetime.utcnow().date(),
            ),
        )

        assert response.status_code == 200, response.json()
        answer_id = response.json()["result"][0]["answerDates"][0]["answerId"]

        # test completions
        response = await client.get(
            url=self.applets_answers_completions_url,
            query={"fromDate": "2022-10-01"},
        )

        assert response.status_code == 200
        data = response.json()["result"]
        # 2 session applets and 1 for answers
        assert len(data) == 3
        applet_with_answer = next(i for i in data if i["id"] == str(applet.id))

        assert applet_with_answer["id"] == str(applet.id)
        assert applet_with_answer["version"] == applet.version
        assert len(applet_with_answer["activities"]) == 1
        activity_answer_data = applet_with_answer["activities"][0]
        assert set(activity_answer_data.keys()) == {
            "id",
            "answerId",
            "submitId",
            "scheduledEventId",
            "localEndDate",
            "localEndTime",
        }
        assert activity_answer_data["answerId"] == answer_id
        assert activity_answer_data["scheduledEventId"] == "eventId"
        assert activity_answer_data["localEndDate"] == "2022-10-01"
        assert activity_answer_data["localEndTime"] == "12:35:00"
        for applet_data in data:
            if applet_data["id"] != str(applet.id):
                assert not applet_data["activities"]
                assert not applet_data["activityFlows"]

    @pytest.mark.usefixtures("user_reviewer_applet_one")
    async def test_summary_restricted_for_reviewer_if_external_respondent(self, mock_kiq_report, client, tom, applet):
        await client.login(self.login_url, tom.email_encrypted, "Test1234!")

        create_data = dict(
            submit_id=str(uuid.uuid4()),
            applet_id=str(applet.id),
            version=applet.version,
            activity_id=str(applet.activities[0].id),
            answer=dict(
                user_public_key="user key",
                answer=json.dumps(
                    dict(
                        value=str(uuid.uuid4()),
                        additional_text=None,
                    )
                ),
                item_ids=[str(applet.activities[0].items[0].id)],
                identifier="some identifier",
                scheduled_time=1690188679657,
                start_time=1690188679657,
                end_time=1690188731636,
            ),
            client=dict(
                appId="mindlogger-mobile",
                appVersion="0.21.48",
                width=819,
                height=1080,
            ),
        )

        response = await client.post(self.answer_url, data=create_data)
        assert response.status_code == 201

        await client.logout()
        await client.login(self.login_url, "user@example.com", "Test1234!")

        response = await client.get(
            self.summary_activities_url.format(
                applet_id=str(applet.id),
            )
        )

        assert response.status_code == 403

    async def test_public_answer_with_zero_start_time_end_time_timestamps(
        self, mock_kiq_report, client, tom, public_applet
    ):
        create_data = dict(
            submit_id=str(uuid.uuid4()),
            applet_id=str(public_applet.id),
            version=public_applet.version,
            activity_id=str(public_applet.activities[0].id),
            created_at=1690188731636,
            answer=dict(
                user_public_key="user key",
                events=json.dumps(dict(events=["event1", "event2"])),
                answer=json.dumps(
                    dict(
                        value=str(uuid.uuid4()),
                        additional_text=None,
                    )
                ),
                item_ids=[str(public_applet.activities[0].items[0].id)],
                scheduled_time=1690188679657,
                start_time=0,
                end_time=0,
            ),
            client=dict(
                appId="mindlogger-mobile",
                appVersion="0.21.48",
                width=819,
                height=1080,
            ),
        )

        response = await client.post(self.public_answer_url, data=create_data)

        assert response.status_code == 201
