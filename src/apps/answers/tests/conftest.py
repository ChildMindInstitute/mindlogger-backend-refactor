import uuid
from typing import cast

import pytest
from pytest_mock import MockerFixture
from sqlalchemy.ext.asyncio import AsyncSession

from apps.activities.domain.response_type_config import SingleSelectionConfig
from apps.activities.domain.response_values import SingleSelectionValues
from apps.activities.domain.scores_reports import ReportType, ScoresAndReports, Section
from apps.applets.domain.applet_create_update import AppletCreate
from apps.applets.domain.applet_full import AppletFull
from apps.applets.domain.applet_link import CreateAccessLink
from apps.applets.domain.base import AppletReportConfigurationBase
from apps.applets.service.applet import AppletService
from apps.users.db.schemas import UserSchema
from apps.users.domain import User
from apps.workspaces.domain.constants import Role
from apps.workspaces.service.user_applet_access import UserAppletAccessService


@pytest.fixture
async def user_reviewer_applet_one(
    user: UserSchema, session: AsyncSession, mocker: MockerFixture, applet_one: AppletFull, lucy: User
):
    srv = UserAppletAccessService(session, user.id, applet_one.id)
    mocker.patch(
        "apps.workspaces.service.user_applet_access.UserAppletAccessService._get_default_role_meta",
        return_value={"respondents": [str(lucy.id)]},
    )
    await srv.add_role(user.id, Role.REVIEWER)


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


# TODO: investigate why scope class does not work if run all tests in app and if fixute is defined in conftest
@pytest.fixture
async def applet(session: AsyncSession, tom: User, applet_data: AppletCreate) -> AppletFull:
    srv = AppletService(session, tom.id)
    applet = await srv.create(applet_data)
    return applet


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
    # NOTE: Fixture 'applet' with scoped class already bound default applet_id
    applet = await srv.create(applet_create, applet_id=uuid.uuid4())
    return applet
