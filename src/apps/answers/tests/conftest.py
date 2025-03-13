import datetime
import uuid
from typing import cast

import pytest
from pytest_mock import MockerFixture
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.activities.domain.activity_create import ActivityItemCreate
from apps.activities.domain.response_type_config import SingleSelectionConfig
from apps.activities.domain.response_values import SingleSelectionValues
from apps.activities.domain.scores_reports import ReportType, ScoresAndReports, Section
from apps.activity_flows.domain.flow_create import FlowCreate, FlowItemCreate
from apps.answers.db.schemas import AnswerNoteSchema, AnswerSchema
from apps.answers.domain import AnswerNote, ClientMeta
from apps.answers.domain.answers import AnswerAlert, AppletAnswerCreate, AssessmentAnswerCreate, ItemAnswerCreate
from apps.answers.service import AnswerService
from apps.applets.domain.applet_create_update import AppletCreate, AppletUpdate
from apps.applets.domain.applet_full import AppletFull
from apps.applets.domain.applet_link import CreateAccessLink
from apps.applets.domain.base import AppletReportConfigurationBase
from apps.applets.service.applet import AppletService
from apps.shared.enums import Language
from apps.subjects.db.schemas import SubjectSchema
from apps.users.db.schemas import UserSchema
from apps.users.domain import User
from apps.workspaces.domain.constants import Role
from apps.workspaces.service.user_applet_access import UserAppletAccessService


@pytest.fixture
async def user_reviewer_applet_one(
    user: UserSchema, session: AsyncSession, mocker: MockerFixture, applet_one: AppletFull, lucy: User
) -> AppletFull:
    srv = UserAppletAccessService(session, user.id, applet_one.id)
    mocker.patch(
        "apps.workspaces.service.user_applet_access.UserAppletAccessService._get_default_role_meta",
        return_value={"respondents": [str(lucy.id)]},
    )
    await srv.add_role(user.id, Role.REVIEWER)
    return applet_one


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
async def tom_applet_subject(session: AsyncSession, tom: User, applet: AppletFull) -> SubjectSchema:
    query = select(SubjectSchema).where(SubjectSchema.user_id == tom.id, SubjectSchema.applet_id == applet.id)
    res = await session.execute(query, execution_options={"synchronize_session": False})
    model = res.scalars().one()
    return model


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
    reviewable_activity = data.activities[0].copy(deep=True)
    reviewable_activity.name = data.activities[0].name + " review"
    reviewable_activity.is_reviewable = True
    data.activities.append(reviewable_activity)
    applet_create = AppletCreate(**data.dict())
    srv = AppletService(session, tom.id)
    applet = await srv.create(applet_create)
    return applet


@pytest.fixture
def client_meta() -> ClientMeta:
    return ClientMeta(app_id="pytest", app_version="pytest", width=0, height=0)


@pytest.fixture
async def applet_with_flow(
    session: AsyncSession,
    applet_minimal_data: AppletCreate,
    tom: User,
    applet_report_configuration_data: AppletReportConfigurationBase,
) -> AppletFull:
    data = applet_minimal_data.copy(deep=True)
    data.display_name = "applet with flow"

    for i in range(2, 4):
        activity = data.activities[0].copy(deep=True)
        activity.name = data.activities[0].name + f"#{i}"
        activity.key = uuid.uuid4()
        data.activities.append(activity)

    data.activity_flows = [
        FlowCreate(
            name="flow",
            description={Language.ENGLISH: "description"},
            items=[FlowItemCreate(activity_key=data.activities[0].key)],
        ),
        FlowCreate(
            name="flow2",
            description={Language.ENGLISH: "description2"},
            items=[
                FlowItemCreate(activity_key=data.activities[0].key),
                FlowItemCreate(activity_key=data.activities[1].key),
                FlowItemCreate(activity_key=data.activities[2].key),
            ],
        ),
    ]
    data.report_server_ip = applet_report_configuration_data.report_server_ip
    data.report_public_key = applet_report_configuration_data.report_public_key
    data.report_recipients = applet_report_configuration_data.report_recipients
    applet_create = AppletCreate(**data.dict())
    srv = AppletService(session, tom.id)
    applet = await srv.create(applet_create, applet_id=uuid.uuid4())

    return applet


@pytest.fixture
async def applet_with_flow_duplicated_activities(
    session: AsyncSession,
    applet_minimal_data: AppletCreate,
    tom: User,
    applet_report_configuration_data: AppletReportConfigurationBase,
) -> AppletFull:
    data = applet_minimal_data.copy(deep=True)
    data.display_name = "applet with flow"

    data.activity_flows = [
        FlowCreate(
            name="flow",
            description={Language.ENGLISH: "description"},
            items=[
                FlowItemCreate(activity_key=data.activities[0].key),
                FlowItemCreate(activity_key=data.activities[0].key),
            ],
        ),
    ]
    data.report_server_ip = applet_report_configuration_data.report_server_ip
    data.report_public_key = applet_report_configuration_data.report_public_key
    data.report_recipients = applet_report_configuration_data.report_recipients
    applet_create = AppletCreate(**data.dict())
    srv = AppletService(session, tom.id)
    applet = await srv.create(applet_create, applet_id=uuid.uuid4())

    return applet


@pytest.fixture
def answer_item_create(
    applet: AppletFull,
    single_select_item_create: ActivityItemCreate,
) -> ItemAnswerCreate:
    assert applet.activities[0].items[0].response_type == single_select_item_create.response_type
    single_select_item_create.response_values = cast(
        SingleSelectionValues,
        single_select_item_create.response_values,
    )
    option = single_select_item_create.response_values.options[0]
    row_answer = str([{"value": option.value, "text": option.text}])
    encrypted_answer = row_answer
    return ItemAnswerCreate(
        answer=encrypted_answer,
        events=str(["event1", "event2"]),
        item_ids=[i.id for i in applet.activities[0].items],
        identifier="encrypted_identifier",
        scheduled_time=None,
        scheduled_event_id=str(uuid.uuid4()),
        start_time=datetime.datetime.now(datetime.UTC),
        end_time=datetime.datetime.now(datetime.UTC) + datetime.timedelta(seconds=1),
        local_end_date=datetime.datetime.now(datetime.UTC).date() - datetime.timedelta(days=1),
        local_end_time=datetime.time(15, 0),
        user_public_key="public_key",
    )


@pytest.fixture
def answer_create(
    applet: AppletFull,
    answer_item_create: ItemAnswerCreate,
    client_meta: ClientMeta,
) -> AppletAnswerCreate:
    return AppletAnswerCreate(
        applet_id=applet.id,
        version=applet.version,
        submit_id=uuid.uuid4(),
        activity_id=applet.activities[0].id,
        answer=answer_item_create,
        created_at=datetime.datetime.now(datetime.UTC).replace(microsecond=0),
        client=client_meta,
        consent_to_share=False,
    )


@pytest.fixture
def answer_create_applet_one(
    applet_one: AppletFull,
    answer_item_create: ItemAnswerCreate,
    client_meta: ClientMeta,
) -> AppletAnswerCreate:
    return AppletAnswerCreate(
        applet_id=applet_one.id,
        version=applet_one.version,
        submit_id=uuid.uuid4(),
        activity_id=applet_one.activities[0].id,
        answer=answer_item_create,
        created_at=datetime.datetime.now(datetime.UTC).replace(microsecond=0),
        client=client_meta,
    )


@pytest.fixture
def answer_alert(applet: AppletFull) -> AnswerAlert:
    return AnswerAlert(activity_item_id=applet.activities[0].items[0].id, message="answer alert")


@pytest.fixture
def answer_with_alert_create(
    applet: AppletFull,
    answer_item_create: ItemAnswerCreate,
    client_meta: ClientMeta,
    answer_alert: AnswerAlert,
) -> AppletAnswerCreate:
    return AppletAnswerCreate(
        applet_id=applet.id,
        version=applet.version,
        submit_id=uuid.uuid4(),
        activity_id=applet.activities[0].id,
        answer=answer_item_create,
        created_at=datetime.datetime.now(datetime.UTC).replace(microsecond=0),
        client=client_meta,
        alerts=[answer_alert],
        consent_to_share=False,
    )


@pytest.fixture
async def answer(session: AsyncSession, tom: User, answer_create: AppletAnswerCreate) -> AnswerSchema:
    srv = AnswerService(session, tom.id)
    answer = await srv.create_answer(answer_create)
    return answer


@pytest.fixture
def public_answer_create(
    public_applet: AppletFull, answer_item_create: ItemAnswerCreate, client_meta: ClientMeta
) -> AppletAnswerCreate:
    item_create = answer_item_create.copy(deep=True)
    item_create.item_ids = [i.id for i in public_applet.activities[0].items]
    return AppletAnswerCreate(
        applet_id=public_applet.id,
        version=public_applet.version,
        submit_id=uuid.uuid4(),
        activity_id=public_applet.activities[0].id,
        answer=item_create,
        created_at=datetime.datetime.now(datetime.UTC).replace(microsecond=0),
        client=client_meta,
        consent_to_share=False,
    )


@pytest.fixture
def answer_with_flow_create(
    applet_with_flow: AppletFull,
    answer_item_create: ItemAnswerCreate,
    client_meta: ClientMeta,
) -> AppletAnswerCreate:
    return AppletAnswerCreate(
        applet_id=applet_with_flow.id,
        version=applet_with_flow.version,
        submit_id=uuid.uuid4(),
        activity_id=applet_with_flow.activities[0].id,
        answer=answer_item_create,
        created_at=datetime.datetime.now(datetime.UTC).replace(microsecond=0),
        client=client_meta,
        flow_id=applet_with_flow.activity_flows[0].id,
        is_flow_completed=True,
        consent_to_share=False,
    )


@pytest.fixture
async def applet_with_additional_item(applet: AppletFull, session: AsyncSession, tom: User) -> AppletFull:
    data = AppletUpdate(**applet.dict())
    item = data.activities[0].items[0].copy(deep=True)
    item.name += "second"
    item.id = None
    data.activities[0].items.append(item)
    srv = AppletService(session, tom.id)
    updated_applet = await srv.update(applet.id, data)
    return updated_applet


@pytest.fixture
def answer_reviewable_activity_create(
    applet_with_reviewable_activity: AppletFull, answer_item_create: ItemAnswerCreate, client_meta: ClientMeta
) -> AppletAnswerCreate:
    item_create = answer_item_create.copy(deep=True)
    activity = next(i for i in applet_with_reviewable_activity.activities if not i.is_reviewable)
    item_create.item_ids = [i.id for i in activity.items]
    return AppletAnswerCreate(
        applet_id=applet_with_reviewable_activity.id,
        version=applet_with_reviewable_activity.version,
        submit_id=uuid.uuid4(),
        activity_id=activity.id,
        answer=item_create,
        created_at=datetime.datetime.now(datetime.UTC).replace(microsecond=0),
        client=client_meta,
        consent_to_share=False,
    )


@pytest.fixture
async def answer_reviewable_activity(
    session: AsyncSession,
    tom: User,
    answer_reviewable_activity_create: AppletAnswerCreate,
) -> AnswerSchema:
    srv = AnswerService(session, tom.id)
    answer = await srv.create_answer(answer_reviewable_activity_create)
    return answer


@pytest.fixture
def answer_reviewable_activity_with_tz_offset_create(
    answer_reviewable_activity_create: AppletAnswerCreate,
) -> AppletAnswerCreate:
    data = answer_reviewable_activity_create.copy(deep=True)
    data.submit_id = uuid.uuid4()
    # US/Pacific
    tz_offset = -420
    # To minutes like in api
    data.answer.tz_offset = tz_offset // 60
    return data


@pytest.fixture
async def answer_reviewable_activity_with_ts_offset(
    session: AsyncSession,
    tom: User,
    answer_reviewable_activity_with_tz_offset_create: AppletAnswerCreate,
) -> AnswerSchema:
    srv = AnswerService(session, tom.id)
    answer = await srv.create_answer(answer_reviewable_activity_with_tz_offset_create)
    return answer


@pytest.fixture
def assessment_create(
    tom: User, answer_reviewable_activity: AnswerSchema, applet_with_reviewable_activity: AppletFull
) -> AssessmentAnswerCreate:
    # Possible answer need to make correct answer
    activity = next(i for i in applet_with_reviewable_activity.activities if i.is_reviewable)
    return AssessmentAnswerCreate(
        answer="assessment answer",
        item_ids=[(i.id) for i in activity.items],
        assessment_version_id=answer_reviewable_activity.activity_history_id,
        # By some reasons from UI we have uuid (user_id)
        reviewer_public_key=str(tom.id),
    )


@pytest.fixture
async def assessment(
    session: AsyncSession,
    tom: User,
    answer_reviewable_activity: AnswerSchema,
    assessment_create: AssessmentAnswerCreate,
) -> None:
    srv = AnswerService(session, tom.id)
    await srv.create_assessment_answer(
        answer_reviewable_activity.applet_id, answer_reviewable_activity.id, assessment_create
    )


@pytest.fixture
def note_create_data() -> AnswerNote:
    return AnswerNote(note="note")


@pytest.fixture
async def answer_note(
    session: AsyncSession, tom: User, answer: AnswerSchema, note_create_data: AnswerNote
) -> AnswerNoteSchema:
    return await AnswerService(session, tom.id).add_answer_note(
        answer.applet_id, answer.id, uuid.UUID(answer.activity_history_id.split("_")[0]), note=note_create_data.note
    )


@pytest.fixture
async def answer_arbitrary(
    session: AsyncSession, arbitrary_session: AsyncSession, tom: User, answer_create: AppletAnswerCreate
) -> AnswerSchema:
    srv = AnswerService(session, tom.id, arbitrary_session)
    answer = await srv.create_answer(answer_create)
    return answer


@pytest.fixture
async def answer_reviewable_activity_arbitrary(
    session: AsyncSession,
    arbitrary_session: AsyncSession,
    tom: User,
    answer_reviewable_activity_create: AppletAnswerCreate,
) -> AnswerSchema:
    srv = AnswerService(session, tom.id, arbitrary_session)
    answer = await srv.create_answer(answer_reviewable_activity_create)
    return answer


@pytest.fixture
def assessment_arbitrary_create(
    tom: User, answer_reviewable_activity_arbitrary: AnswerSchema, applet_with_reviewable_activity: AppletFull
) -> AssessmentAnswerCreate:
    # Possible answer need to make correct answer
    activity = next(i for i in applet_with_reviewable_activity.activities if i.is_reviewable)
    return AssessmentAnswerCreate(
        answer="assessment answer",
        item_ids=[(i.id) for i in activity.items],
        assessment_version_id=answer_reviewable_activity_arbitrary.activity_history_id,
        # By some reasons from UI we have uuid (user_id)
        reviewer_public_key=str(tom.id),
    )


@pytest.fixture
async def assessment_arbitrary(
    session: AsyncSession,
    arbitrary_session: AsyncSession,
    tom: User,
    answer_reviewable_activity_arbitrary: AnswerSchema,
    assessment_arbitrary_create: AssessmentAnswerCreate,
) -> None:
    srv = AnswerService(session, tom.id, arbitrary_session)
    await srv.create_assessment_answer(
        answer_reviewable_activity_arbitrary.applet_id,
        answer_reviewable_activity_arbitrary.id,
        assessment_arbitrary_create,
    )


@pytest.fixture
async def answer_note_arbitrary(
    session: AsyncSession,
    arbitrary_session: AsyncSession,
    tom: User,
    answer_arbitrary: AnswerSchema,
    note_create_data: AnswerNote,
) -> AnswerNoteSchema:
    return await AnswerService(session, tom.id, arbitrary_session).add_answer_note(
        answer_arbitrary.applet_id,
        answer_arbitrary.id,
        uuid.UUID(answer_arbitrary.activity_history_id.split("_")[0]),
        note=note_create_data.note,
    )


@pytest.fixture
def tom_answer_create_data(tom, applet_with_reviewable_activity) -> AppletAnswerCreate:
    return AppletAnswerCreate(
        applet_id=applet_with_reviewable_activity.id,
        version=applet_with_reviewable_activity.version,
        submit_id=uuid.uuid4(),
        activity_id=applet_with_reviewable_activity.activities[0].id,
        answer=ItemAnswerCreate(
            item_ids=[applet_with_reviewable_activity.activities[0].items[0].id],
            start_time=datetime.datetime.now(datetime.UTC),
            end_time=datetime.datetime.now(datetime.UTC),
            user_public_key=str(tom.id),
        ),
        client=ClientMeta(app_id=f"{uuid.uuid4()}", app_version="1.1", width=984, height=623),
        consent_to_share=False,
    )


@pytest.fixture
def tom_answer_assessment_create_data(tom, applet_with_reviewable_activity) -> AssessmentAnswerCreate:
    activity_assessment_id = applet_with_reviewable_activity.activities[1].id
    return AssessmentAnswerCreate(
        answer="0x00",
        item_ids=[applet_with_reviewable_activity.activities[1].items[0].id],
        reviewer_public_key=f"{tom.id}",
        assessment_version_id=f"{activity_assessment_id}_{applet_with_reviewable_activity.version}",
    )


@pytest.fixture
async def editor_user_reviewer_applet_one(user: UserSchema, session: AsyncSession, mocker: MockerFixture):
    applet_id = uuid.UUID("92917a56-d586-4613-b7aa-991f2c4b15b1")
    srv = UserAppletAccessService(session, user.id, applet_id)
    await srv.add_role(user.id, Role.EDITOR)


@pytest.fixture
async def applet_with_reviewable_flow(
    session: AsyncSession, applet_minimal_data: AppletCreate, tom: User
) -> AppletFull:
    data = applet_minimal_data.copy(deep=True)
    data.display_name = "applet with reviewable flow"

    second_activity = data.activities[0].copy(deep=True)
    second_activity.name = data.activities[0].name + " second"
    second_activity.key = uuid.uuid4()

    third_activity = data.activities[0].copy(deep=True)
    third_activity.name = data.activities[0].name + " third"
    third_activity.key = uuid.uuid4()
    third_activity.is_reviewable = True

    data.activities.append(second_activity)
    data.activities.append(third_activity)

    data.activity_flows = [
        FlowCreate(
            name="flow",
            description={Language.ENGLISH: "description"},
            items=[
                FlowItemCreate(activity_key=data.activities[0].key),
                FlowItemCreate(activity_key=data.activities[1].key),
            ],
        ),
    ]
    applet_create = AppletCreate(**data.dict())
    srv = AppletService(session, tom.id)
    applet = await srv.create(applet_create, applet_id=uuid.uuid4())
    return applet


@pytest.fixture
def answers_reviewable_submission_create(
    applet_with_reviewable_flow: AppletFull, answer_item_create: ItemAnswerCreate, client_meta: ClientMeta
) -> list[AppletAnswerCreate]:
    item_create = answer_item_create.copy(deep=True)
    activities = []
    flow_items = applet_with_reviewable_flow.activity_flows[0].items
    flow_activity_ids = list(map(lambda x: x.activity_id, flow_items))
    submit_id = uuid.uuid4()
    for activity_id in flow_activity_ids:
        activity = next(filter(lambda x: x.id == activity_id, applet_with_reviewable_flow.activities))
        item_create.item_ids = [i.id for i in activity.items]
        answer_create_data = AppletAnswerCreate(
            applet_id=applet_with_reviewable_flow.id,
            version=applet_with_reviewable_flow.version,
            submit_id=submit_id,
            activity_id=activity.id,
            answer=item_create,
            created_at=datetime.datetime.now(datetime.UTC).replace(microsecond=0),
            client=client_meta,
            flow_id=applet_with_reviewable_flow.activity_flows[0].id,
        )
        activities.append(answer_create_data)
    return activities


@pytest.fixture
async def answers_reviewable_submission(
    session: AsyncSession,
    tom: User,
    answers_reviewable_submission_create: list[AppletAnswerCreate],
) -> list[AnswerSchema]:
    srv = AnswerService(session, tom.id)
    answer_schemas = []
    size_t = len(answers_reviewable_submission_create)
    for i in range(size_t):
        answer_data = answers_reviewable_submission_create[i]
        if i == (size_t - 1):
            answer_data.is_flow_completed = True
        answer = await srv.create_answer(answer_data)
        answer_schemas.append(answer)
    return answer_schemas


@pytest.fixture
async def answers_reviewable_submission_arbitrary(
    session: AsyncSession,
    arbitrary_session: AsyncSession,
    tom: User,
    answers_reviewable_submission_create: list[AppletAnswerCreate],
) -> list[AnswerSchema]:
    srv = AnswerService(session, tom.id, arbitrary_session)
    answer_schemas = []
    size_t = len(answers_reviewable_submission_create)
    for i in range(size_t):
        answer_data = answers_reviewable_submission_create[i]
        if i == (size_t - 1):
            answer_data.is_flow_completed = True
        answer = await srv.create_answer(answer_data)
        answer_schemas.append(answer)
    return answer_schemas


@pytest.fixture
def assessment_submission_create(
    tom: User, answers_reviewable_submission: list[AnswerSchema], applet_with_reviewable_flow: AppletFull
) -> AssessmentAnswerCreate:
    assessment_activity = next(i for i in applet_with_reviewable_flow.activities if i.is_reviewable)
    last_flow_answer: AnswerSchema = next(filter(lambda a: a.is_flow_completed, answers_reviewable_submission))
    return AssessmentAnswerCreate(
        answer="assessment answer",
        item_ids=[(i.id) for i in assessment_activity.items],
        assessment_version_id=f"{assessment_activity.id}_{applet_with_reviewable_flow.version}",
        reviewer_public_key=str(tom.id),
        reviewed_flow_submit_id=last_flow_answer.submit_id,
    )


@pytest.fixture
async def assessment_for_submission(
    session: AsyncSession,
    tom: User,
    answers_reviewable_submission: list[AnswerSchema],
    assessment_submission_create: AssessmentAnswerCreate,
) -> None:
    last_flow_answer: AnswerSchema = next(filter(lambda a: a.is_flow_completed, answers_reviewable_submission))
    srv = AnswerService(session, tom.id)
    await srv.create_assessment_answer(last_flow_answer.applet_id, last_flow_answer.id, assessment_submission_create)


@pytest.fixture
async def assessment_for_submission_arbitrary(
    session: AsyncSession,
    arbitrary_session: AsyncSession,
    tom: User,
    answers_reviewable_submission_arbitrary: list[AnswerSchema],
    assessment_submission_create: AssessmentAnswerCreate,
) -> None:
    last_flow_answer: AnswerSchema = next(
        filter(lambda a: a.is_flow_completed, answers_reviewable_submission_arbitrary)
    )
    srv = AnswerService(session, tom.id, arbitrary_session=arbitrary_session)
    await srv.create_assessment_answer(last_flow_answer.applet_id, last_flow_answer.id, assessment_submission_create)


@pytest.fixture
async def submission_note(
    session: AsyncSession, tom: User, answers_reviewable_submission: list[AnswerSchema], note_create_data: AnswerNote
) -> AnswerNoteSchema:
    last_flow_answer: AnswerSchema = next(filter(lambda a: a.is_flow_completed, answers_reviewable_submission))
    return await AnswerService(session, tom.id).add_submission_note(
        last_flow_answer.applet_id,
        last_flow_answer.submit_id,
        uuid.UUID(last_flow_answer.flow_history_id.split("_")[0]),
        note=note_create_data.note,
    )


@pytest.fixture
async def applet__activity_turned_into_assessment(
    session: AsyncSession, tom: User, applet_data: AppletCreate
) -> AppletFull:
    """
    Applet with one Activity0 updated into applet with Activity0(is_reviewable=True) and Activity1
    All activities has no answers
    """
    srv = AppletService(session, tom.id)
    applet = await srv.create(applet_data)
    data = AppletUpdate(**applet.dict())

    activity_new = data.activities[0].copy(deep=True)
    activity_new.id = uuid.uuid4()
    activity_new.key = uuid.uuid4()
    for i in range(len(activity_new.items)):
        activity_new.items[i].id = uuid.uuid4()
    activity_new.name = "New activity"
    data.activities.append(activity_new)

    data.activities[0].is_reviewable = True
    data.activities[0].name = "Reviewer assessment"
    updated_applet = await srv.update(applet.id, data)
    return updated_applet


@pytest.fixture
async def applet__deleted_activity_without_answers(
    session: AsyncSession, tom: User, applet_data: AppletCreate
) -> AppletFull:
    """
    Applet with one Activity0 updated into applet with Activity1 and deleted Activity1
    All activities has no answers
    """
    srv = AppletService(session, tom.id)
    applet = await srv.create(applet_data)
    data = AppletUpdate(**applet.dict())

    activity_new = data.activities[0].copy(deep=True)
    activity_new.id = uuid.uuid4()
    activity_new.key = uuid.uuid4()
    for i in range(len(activity_new.items)):
        activity_new.items[i].id = uuid.uuid4()
    activity_new.name = "New activity"
    data.activities = [activity_new]
    updated_applet = await srv.update(applet.id, data)
    return updated_applet


@pytest.fixture
async def applet__deleted_flow_without_answers(
    session: AsyncSession, tom: User, applet_with_flow: AppletFull
) -> AppletFull:
    srv = AppletService(session, tom.id)
    data = applet_with_flow.dict()
    activity_flow = data["activity_flows"][0]
    for i in range(len(activity_flow["items"])):
        activity_flow["items"][i]["activity_key"] = data["activities"][0]["key"]
    data["activity_flows"] = [activity_flow]
    update_data = AppletUpdate(**data)
    updated_applet = await srv.update(applet_with_flow.id, update_data)
    return updated_applet


@pytest.fixture
async def applet__with_ordered_activities(session: AsyncSession, tom: User, applet_data: AppletCreate) -> AppletFull:
    srv = AppletService(session, tom.id)
    applet = await srv.create(applet_data)
    data = AppletUpdate(**applet.dict())
    activities = []
    for i in range(4):
        activity_new = data.activities[0].copy(deep=True)
        activity_new.id = uuid.uuid4()
        activity_new.key = uuid.uuid4()
        for j in range(len(activity_new.items)):
            activity_new.items[j].id = uuid.uuid4()
        activity_new.name = f"ordered_activity_{i}"
        activities.append(activity_new)

    # create version with all activities
    data.activities = activities
    updated_applet = await srv.update(applet.id, data)
    return updated_applet


@pytest.fixture
async def answer_ident_series(
    session: AsyncSession, tom: User, answer_create: AppletAnswerCreate
) -> list[AnswerSchema]:
    srv = AnswerService(session, tom.id)
    answers = []
    for ident in ("Ident1", "Ident2", None):
        answer_create.submit_id = uuid.uuid4()
        answer_create.answer.identifier = ident
        answer = await srv.create_answer(answer_create)
        answers.append(answer)
    return answers
