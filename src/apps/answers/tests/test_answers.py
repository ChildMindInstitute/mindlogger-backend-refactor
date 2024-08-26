import datetime
import http
import re
import uuid
from collections import defaultdict
from typing import Any, AsyncGenerator, Tuple, cast
from unittest.mock import AsyncMock

import pytest
from pydantic import EmailStr
from pytest import Config, FixtureRequest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.activities.domain.activity_update import ActivityUpdate
from apps.answers.crud import AnswerItemsCRUD
from apps.answers.crud.answers import AnswersCRUD
from apps.answers.db.schemas import AnswerItemSchema, AnswerNoteSchema, AnswerSchema
from apps.answers.domain import AnswerNote, AppletAnswerCreate, AssessmentAnswerCreate, ClientMeta, ItemAnswerCreate
from apps.answers.service import AnswerService
from apps.applets.domain.applet_create_update import AppletUpdate
from apps.applets.domain.applet_full import AppletFull
from apps.applets.errors import InvalidVersionError
from apps.applets.service import AppletService
from apps.mailing.services import TestMail
from apps.shared.test import BaseTest
from apps.shared.test.client import TestClient
from apps.subjects.constants import Relation
from apps.subjects.db.schemas import SubjectSchema
from apps.subjects.domain import Subject, SubjectCreate
from apps.subjects.services import SubjectsService
from apps.users import User
from apps.users.cruds.user import UsersCRUD
from apps.users.domain import UserCreate
from apps.users.tests.fixtures.users import _get_or_create_user
from apps.workspaces.crud.user_applet_access import UserAppletAccessCRUD
from apps.workspaces.db.schemas import UserAppletAccessSchema
from apps.workspaces.domain.constants import Role
from apps.workspaces.service.user_applet_access import UserAppletAccessService
from infrastructure.utility import RedisCacheTest


@pytest.fixture(params=["none", "respondent", "subject"])
async def identifiers_query(request, tom_applet_subject: SubjectSchema):
    params_map = {
        "none": {},
        "respondent": {"respondentId": str(tom_applet_subject.user_id)},
        "subject": {"targetSubjectId": str(tom_applet_subject.id)},
    }
    return params_map[request.param]


def note_url_path_data(answer: AnswerSchema) -> dict[str, Any]:
    return {
        "applet_id": answer.applet_id,
        "answer_id": answer.id,
        "activity_id": answer.activity_history_id.split("_")[0],
    }


@pytest.fixture(scope="session", autouse=True)
async def sam(sam_create: UserCreate, global_session: AsyncSession, pytestconfig: Config) -> AsyncGenerator:
    crud = UsersCRUD(global_session)
    user = await _get_or_create_user(
        crud, sam_create, global_session, uuid.UUID("35c4ed0a-1a09-4c16-b555-6d6ad639ac05")
    )
    yield user
    if not pytestconfig.getoption("--keepdb"):
        await crud._delete(id=user.id)
        await global_session.commit()


@pytest.fixture(scope="session", autouse=True)
def sam_create() -> UserCreate:
    return UserCreate(
        email=EmailStr("sam@mindlogger.com"),
        password="Test1234!",
        first_name="Sam",
        last_name="Smith",
    )


@pytest.fixture
async def applet_one_sam_respondent(session: AsyncSession, applet_one: AppletFull, tom: User, sam: User) -> AppletFull:
    await UserAppletAccessService(session, tom.id, applet_one.id).add_role(sam.id, Role.RESPONDENT)
    return applet_one


@pytest.fixture
async def applet_one_sam_subject(session: AsyncSession, applet_one: AppletFull, sam: User) -> Subject:
    applet_id = applet_one.id
    user_id = sam.id
    query = select(SubjectSchema).where(SubjectSchema.user_id == user_id, SubjectSchema.applet_id == applet_id)
    res = await session.execute(query, execution_options={"synchronize_session": False})
    model = res.scalars().one()
    return Subject.from_orm(model)


@pytest.fixture
async def bob_reviewer_in_applet_with_reviewable_activity(session, tom, bob, applet_with_reviewable_activity) -> User:
    tom_subject = await SubjectsService(session, tom.id).get_by_user_and_applet(
        tom.id, applet_with_reviewable_activity.id
    )
    assert tom_subject, "Must have an subject for submitting answers"
    await UserAppletAccessCRUD(session).save(
        UserAppletAccessSchema(
            user_id=bob.id,
            applet_id=applet_with_reviewable_activity.id,
            role=Role.REVIEWER,
            owner_id=tom.id,
            invitor_id=tom.id,
            meta=dict(subjects=[str(tom_subject.id)]),
            nickname=str(uuid.uuid4()),
        )
    )
    return bob


@pytest.fixture
async def lucy_manager_in_applet_with_reviewable_activity(session, tom, lucy, applet_with_reviewable_activity) -> User:
    await UserAppletAccessCRUD(session).save(
        UserAppletAccessSchema(
            user_id=lucy.id,
            applet_id=applet_with_reviewable_activity.id,
            role=Role.MANAGER,
            owner_id=tom.id,
            invitor_id=tom.id,
            meta=dict(),
            nickname=str(uuid.uuid4()),
        )
    )
    return lucy


@pytest.fixture
async def lucy_manager_in_applet_with_reviewable_flow(session, tom, lucy, applet_with_reviewable_flow) -> User:
    await UserAppletAccessCRUD(session).save(
        UserAppletAccessSchema(
            user_id=lucy.id,
            applet_id=applet_with_reviewable_flow.id,
            role=Role.MANAGER,
            owner_id=tom.id,
            invitor_id=tom.id,
            meta=dict(),
            nickname=str(uuid.uuid4()),
        )
    )
    return lucy


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
async def tom_answer_item_for_applet(tom: User, applet: AppletFull, session: AsyncSession, tom_applet_subject):
    answer = await AnswersCRUD(session).create(
        AnswerSchema(
            applet_id=applet.id,
            version=applet.version,
            submit_id=uuid.uuid4(),
            client=dict(
                appId="mindlogger-mobile",
                appVersion="0.21.48",
            ),
            applet_history_id=f"{applet.id}_{applet.version}",
            activity_history_id=f"{applet.activities[0].id}_{applet.version}",
            respondent_id=tom.id,
            target_subject_id=tom_applet_subject.id,
            source_subject_id=tom_applet_subject.id,
        )
    )
    return dict(
        answer_id=answer.id,
        respondent_id=tom.id,
        answer=uuid.uuid4().hex,
        item_ids=[str(item.id) for item in applet.activities[0].items],
        start_datetime=datetime.datetime.utcnow(),
        end_datetime=datetime.datetime.utcnow(),
        is_assessment=False,
    )


@pytest.fixture
async def answer_shell_account_target(tom: User, applet: AppletFull, session: AsyncSession):
    shell_account = await SubjectsService(session, tom.id).create(
        SubjectCreate(
            applet_id=applet.id,
            creator_id=tom.id,
            first_name="first_name",
            last_name="last_name",
            secret_user_id=f"{uuid.uuid4()}",
            tag="Child",
        )
    )

    answer = await AnswerService(session, tom.id).create_answer(
        AppletAnswerCreate(
            applet_id=applet.id,
            version=applet.version,
            submit_id=uuid.uuid4(),
            activity_id=applet.activities[0].id,
            answer=ItemAnswerCreate(
                item_ids=[applet.activities[0].items[0].id],
                start_time=datetime.datetime.utcnow(),
                end_time=datetime.datetime.utcnow(),
                user_public_key=str(tom.id),
            ),
            client=ClientMeta(app_id=f"{uuid.uuid4()}", app_version="1.1", width=984, height=623),
            target_subject_id=shell_account.id,
            source_subject_id=shell_account.id,
        )
    )

    tom_subject = await SubjectsService(session, tom.id).get_by_user_and_applet(tom.id, applet.id)
    assert tom_subject

    return dict(
        answer_id=answer.id,
        respondent_subject_id=tom_subject.id,
        respondent_subject_tag="Team",
        respondent_nickname=tom_subject.nickname,
        respondent_secret_user_id=tom_subject.secret_user_id,
        target_subject_id=shell_account.id,
        target_subject_tag="Child",
        target_nickname=shell_account.nickname,
        target_secret_user_id=shell_account.secret_user_id,
        source_subject_id=shell_account.id,
        source_subject_tag="Child",
        source_nickname=shell_account.nickname,
        source_secret_user_id=shell_account.secret_user_id,
        start_datetime=datetime.datetime.utcnow(),
        end_datetime=datetime.datetime.utcnow(),
    )


@pytest.fixture
async def tom_answer_on_reviewable_applet(
    session: AsyncSession, tom: User, applet_with_reviewable_activity: AppletFull
) -> AnswerSchema:
    answer_service = AnswerService(session, tom.id)
    return await answer_service.create_answer(
        AppletAnswerCreate(
            applet_id=applet_with_reviewable_activity.id,
            version=applet_with_reviewable_activity.version,
            submit_id=uuid.uuid4(),
            activity_id=applet_with_reviewable_activity.activities[0].id,
            answer=ItemAnswerCreate(
                item_ids=[applet_with_reviewable_activity.activities[0].items[0].id],
                start_time=datetime.datetime.utcnow(),
                end_time=datetime.datetime.utcnow(),
                user_public_key=str(tom.id),
            ),
            client=ClientMeta(app_id=f"{uuid.uuid4()}", app_version="1.1", width=984, height=623),
        )
    )


@pytest.fixture
async def lucy_answer(session: AsyncSession, lucy: User, applet: AppletFull) -> AnswerSchema:
    answer_service = AnswerService(session, lucy.id)
    return await answer_service.create_answer(
        AppletAnswerCreate(
            applet_id=applet.id,
            version=applet.version,
            submit_id=uuid.uuid4(),
            activity_id=applet.activities[0].id,
            answer=ItemAnswerCreate(
                item_ids=[applet.activities[0].items[0].id],
                start_time=datetime.datetime.utcnow(),
                end_time=datetime.datetime.utcnow(),
                user_public_key=str(lucy.id),
            ),
            client=ClientMeta(app_id=f"{uuid.uuid4()}", app_version="1.1", width=984, height=623),
        )
    )


@pytest.fixture
async def tom_answer_activity_flow(session: AsyncSession, tom: User, applet_with_flow: AppletFull) -> AnswerSchema:
    answer_service = AnswerService(session, tom.id)
    return await answer_service.create_answer(
        AppletAnswerCreate(
            applet_id=applet_with_flow.id,
            version=applet_with_flow.version,
            submit_id=uuid.uuid4(),
            flow_id=applet_with_flow.activity_flows[0].id,
            is_flow_completed=True,
            activity_id=applet_with_flow.activities[0].id,
            answer=ItemAnswerCreate(
                item_ids=[applet_with_flow.activities[0].items[0].id],
                start_time=datetime.datetime.utcnow(),
                end_time=datetime.datetime.utcnow(),
                user_public_key=str(tom.id),
                identifier="encrypted_identifier",
            ),
            client=ClientMeta(app_id=f"{uuid.uuid4()}", app_version="1.1", width=984, height=623),
        )
    )


@pytest.fixture
async def tom_answer_activity_flow_incomplete(
    session: AsyncSession, tom: User, applet_with_flow: AppletFull
) -> AnswerSchema:
    answer_service = AnswerService(session, tom.id)
    return await answer_service.create_answer(
        AppletAnswerCreate(
            applet_id=applet_with_flow.id,
            version=applet_with_flow.version,
            submit_id=uuid.uuid4(),
            flow_id=applet_with_flow.activity_flows[0].id,
            is_flow_completed=False,
            activity_id=applet_with_flow.activities[0].id,
            answer=ItemAnswerCreate(
                item_ids=[applet_with_flow.activities[0].items[0].id],
                start_time=datetime.datetime.utcnow(),
                end_time=datetime.datetime.utcnow(),
                user_public_key=str(tom.id),
                identifier="encrypted_identifier",
            ),
            client=ClientMeta(app_id=f"{uuid.uuid4()}", app_version="1.1", width=984, height=623),
        )
    )


@pytest.fixture
def applet_with_flow_answer_create(applet_with_flow: AppletFull) -> list[AppletAnswerCreate]:
    submit_id = uuid.uuid4()
    answer_data = dict(
        applet_id=applet_with_flow.id,
        version=applet_with_flow.version,
        client=ClientMeta(app_id=f"{uuid.uuid4()}", app_version="1.1", width=984, height=623),
    )
    answer_item_data = dict(
        start_time=datetime.datetime.utcnow(),
        end_time=datetime.datetime.utcnow(),
        user_public_key=str(uuid.uuid4()),
    )
    answers = [
        # flow#1 submission#1
        AppletAnswerCreate(
            submit_id=uuid.uuid4(),
            flow_id=applet_with_flow.activity_flows[0].id,
            is_flow_completed=True,
            activity_id=applet_with_flow.activities[0].id,
            answer=ItemAnswerCreate(
                item_ids=[applet_with_flow.activities[0].items[0].id],
                identifier="encrypted_identifier",
                **answer_item_data,
            ),
            **answer_data,
        ),
        # flow#2 submission#1
        AppletAnswerCreate(
            submit_id=submit_id,
            flow_id=applet_with_flow.activity_flows[1].id,
            is_flow_completed=False,
            activity_id=applet_with_flow.activities[0].id,
            answer=ItemAnswerCreate(
                item_ids=[applet_with_flow.activities[0].items[0].id],
                identifier="encrypted_identifierf2a1",
                **answer_item_data,
            ),
            **answer_data,
        ),
        AppletAnswerCreate(
            submit_id=submit_id,
            flow_id=applet_with_flow.activity_flows[1].id,
            is_flow_completed=True,
            activity_id=applet_with_flow.activities[1].id,
            answer=ItemAnswerCreate(item_ids=[applet_with_flow.activities[1].items[0].id], **answer_item_data),
            **answer_data,
        ),
        # flow#1 submission#2
        AppletAnswerCreate(
            submit_id=uuid.uuid4(),
            flow_id=applet_with_flow.activity_flows[0].id,
            is_flow_completed=True,
            activity_id=applet_with_flow.activities[0].id,
            answer=ItemAnswerCreate(
                item_ids=[applet_with_flow.activities[0].items[0].id],
                identifier="encrypted_identifierf1a2",
                **answer_item_data,
            ),
            **answer_data,
        ),
    ]
    return answers


@pytest.fixture
async def tom_answer_activity_flow_multiple(
    session: AsyncSession, tom: User, applet_with_flow_answer_create
) -> list[AnswerSchema]:
    answer_service = AnswerService(session, tom.id)
    answers = []
    for _answer in applet_with_flow_answer_create:
        answer = await answer_service.create_answer(_answer)
        answers.append(answer)

    return answers


@pytest.fixture
async def tom_answer_activity_no_flow(session: AsyncSession, tom: User, applet_with_flow: AppletFull) -> AnswerSchema:
    answer_service = AnswerService(session, tom.id)
    return await answer_service.create_answer(
        AppletAnswerCreate(
            applet_id=applet_with_flow.id,
            version=applet_with_flow.version,
            submit_id=uuid.uuid4(),
            is_flow_completed=True,
            activity_id=applet_with_flow.activities[0].id,
            answer=ItemAnswerCreate(
                item_ids=[applet_with_flow.activities[0].items[0].id],
                start_time=datetime.datetime.utcnow(),
                end_time=datetime.datetime.utcnow(),
                user_public_key=str(tom.id),
            ),
            client=ClientMeta(app_id=f"{uuid.uuid4()}", app_version="1.1", width=984, height=623),
        )
    )


@pytest.fixture
async def tom_review_answer(
    session: AsyncSession,
    tom: User,
    applet_with_reviewable_activity: AppletFull,
    tom_answer_on_reviewable_applet: AnswerSchema,
):
    applet_id = applet_with_reviewable_activity.id
    activity_assessment_id = applet_with_reviewable_activity.activities[1].id
    assessment = AssessmentAnswerCreate(
        answer=uuid.uuid4().hex,
        item_ids=[applet_with_reviewable_activity.activities[1].items[0].id],
        reviewer_public_key=f"{tom.id}",
        assessment_version_id=f"{activity_assessment_id}_{applet_with_reviewable_activity.version}",
    )
    await AnswerService(session, tom.id).create_assessment_answer(
        applet_id, tom_answer_on_reviewable_applet.id, assessment
    )


@pytest.fixture
async def bob_review_answer(
    session: AsyncSession,
    bob: User,
    applet_with_reviewable_activity: AppletFull,
    tom_answer_on_reviewable_applet: AnswerSchema,
):
    applet_id = applet_with_reviewable_activity.id
    activity_assessment_id = applet_with_reviewable_activity.activities[1].id
    assessment = AssessmentAnswerCreate(
        answer=uuid.uuid4().hex,
        item_ids=[applet_with_reviewable_activity.activities[1].items[0].id],
        reviewer_public_key=f"{bob.id}",
        assessment_version_id=f"{activity_assessment_id}_{applet_with_reviewable_activity.version}",
    )
    await AnswerService(session, bob.id).create_assessment_answer(
        applet_id, tom_answer_on_reviewable_applet.id, assessment
    )


@pytest.fixture
async def lucy_review_answer(
    session: AsyncSession,
    lucy: User,
    applet_with_reviewable_activity: AppletFull,
    tom_answer_on_reviewable_applet: AnswerSchema,
):
    applet_id = applet_with_reviewable_activity.id
    activity_assessment_id = applet_with_reviewable_activity.activities[1].id
    assessment = AssessmentAnswerCreate(
        answer=uuid.uuid4().hex,
        item_ids=[applet_with_reviewable_activity.activities[1].items[0].id],
        reviewer_public_key=f"{lucy.id}",
        assessment_version_id=f"{activity_assessment_id}_{applet_with_reviewable_activity.version}",
    )
    await AnswerService(session, lucy.id).create_assessment_answer(
        applet_id, tom_answer_on_reviewable_applet.id, assessment
    )


@pytest.fixture
async def tom_answer_on_applet_with_alert(
    mock_kiq_report: AsyncMock,
    tom: User,
    answer_with_alert_create: AppletAnswerCreate,
    tom_applet_subject: Subject,
    redis: RedisCacheTest,
    session: AsyncSession,
) -> AnswerSchema:
    return await AnswerService(session, tom.id).create_answer(answer_with_alert_create)


@pytest.fixture
async def tom_answer(tom: User, session: AsyncSession, answer_create: AppletAnswerCreate) -> AnswerSchema:
    return await AnswerService(session, tom.id).create_answer(answer_create)


@pytest.fixture
async def submission_assessment_answer(
    tom: User,
    session: AsyncSession,
    assessment_submission_create: AssessmentAnswerCreate,
    applet_with_reviewable_flow: AppletFull,
) -> AnswerItemSchema | None:
    service = AnswerService(session, tom.id, session)
    assert assessment_submission_create.reviewed_flow_submit_id
    answer = await service.get_submission_last_answer(assessment_submission_create.reviewed_flow_submit_id)
    assert answer
    submission_id = assessment_submission_create.reviewed_flow_submit_id
    answer_service = AnswerService(session, tom.id)
    await answer_service.create_assessment_answer(
        applet_with_reviewable_flow.id, answer.id, assessment_submission_create, submission_id
    )
    return await AnswerItemsCRUD(session).get_assessment(answer.id, tom.id)


@pytest.fixture
async def submission_answer(
    client: TestClient,
    tom: User,
    answers_reviewable_submission: list[AnswerSchema],
):
    return next(filter(lambda a: a.is_flow_completed, answers_reviewable_submission))


@pytest.fixture
async def tom_applet_with_flow_subject(
    session: AsyncSession, tom: User, applet_with_flow: AppletFull
) -> Subject | None:
    return await SubjectsService(session, tom.id).get_by_user_and_applet(tom.id, applet_with_flow.id)


@pytest.fixture
async def tom_answer_activity_flow_not_completed(
    session: AsyncSession, tom: User, applet_with_flow: AppletFull
) -> AnswerSchema:
    answer_service = AnswerService(session, tom.id)
    return await answer_service.create_answer(
        AppletAnswerCreate(
            applet_id=applet_with_flow.id,
            version=applet_with_flow.version,
            submit_id=uuid.uuid4(),
            flow_id=applet_with_flow.activity_flows[1].id,
            is_flow_completed=False,
            activity_id=applet_with_flow.activities[0].id,
            answer=ItemAnswerCreate(
                item_ids=[applet_with_flow.activities[0].items[0].id],
                start_time=datetime.datetime.utcnow(),
                end_time=datetime.datetime.utcnow(),
                user_public_key=str(tom.id),
                identifier="encrypted_identifier",
            ),
            client=ClientMeta(app_id=f"{uuid.uuid4()}", app_version="1.1", width=984, height=623),
        )
    )


@pytest.fixture
async def applet__with_deleted_activities_and_answers(
    session: AsyncSession, tom: User, applet__with_ordered_activities: AppletFull
):
    data = AppletUpdate(**applet__with_ordered_activities.dict())
    applet_service = AppletService(session, tom.id)
    answer_service = AnswerService(session, tom.id)
    applet_id = applet__with_ordered_activities.id
    version = applet__with_ordered_activities.version
    for activity in applet__with_ordered_activities.activities:
        create_data = AppletAnswerCreate(
            applet_id=applet_id,
            version=version,
            submit_id=uuid.uuid4(),
            activity_id=activity.id,
            answer=ItemAnswerCreate(
                item_ids=[activity.items[0].id],
                start_time=datetime.datetime.utcnow(),
                end_time=datetime.datetime.utcnow(),
                user_public_key=str(tom.id),
                identifier="encrypted_identifier",
            ),
            client=ClientMeta(app_id=f"{uuid.uuid4()}", app_version="1.1", width=984, height=623),
        )
        await answer_service.create_answer(create_data)
    # delete first two activities
    data.activities = [ActivityUpdate(**a.dict()) for a in applet__with_ordered_activities.activities[2:]]
    return await applet_service.update(applet_id, data)


@pytest.fixture
async def applet__with_deleted_and_order(
    session: AsyncSession, tom: User, applet_with_flow: AppletFull
) -> Tuple[AppletFull, list[uuid.UUID]]:
    applet_service = AppletService(session, tom.id)
    answer_service = AnswerService(session, tom.id)
    applet_id = applet_with_flow.id
    version = applet_with_flow.version
    flows = applet_with_flow.activity_flows.copy()
    for flow_item in applet_with_flow.activity_flows[0].items:
        activity = next(filter(lambda x: x.id == flow_item.activity_id, applet_with_flow.activities))
        create_data = AppletAnswerCreate(
            applet_id=applet_id,
            version=version,
            submit_id=uuid.uuid4(),
            activity_id=activity.id,
            flow_id=applet_with_flow.activity_flows[0].id,
            is_flow_completed=True,
            answer=ItemAnswerCreate(
                item_ids=[activity.items[0].id],
                start_time=datetime.datetime.utcnow(),
                end_time=datetime.datetime.utcnow(),
                user_public_key=str(tom.id),
                identifier="encrypted_identifier",
            ),
            client=ClientMeta(app_id=f"{uuid.uuid4()}", app_version="1.1", width=984, height=623),
        )
        await answer_service.create_answer(create_data)
    applet_with_flow.activity_flows = [applet_with_flow.activity_flows[1]]
    data = applet_with_flow.dict()
    for i in range(len(data["activity_flows"])):
        activity_flow = data["activity_flows"][i]
        for j in range(len(activity_flow["items"])):
            activity_flow["items"][j]["activity_key"] = data["activities"][j]["key"]
    data_update = AppletUpdate(**data)
    return await applet_service.update(applet_id, data_update), [flows[1].id, flows[0].id]


@pytest.fixture
async def applet_one_lucy_subject(session: AsyncSession, applet_one: AppletFull, tom: User, lucy: User) -> Subject:
    return await SubjectsService(session, tom.id).create(
        SubjectCreate(
            applet_id=applet_one.id,
            creator_id=lucy.id,
            first_name="Shell",
            last_name="Account",
            nickname="shell-account-lucy-0",
            secret_user_id=f"{uuid.uuid4()}",
        )
    )


@pytest.fixture
async def applet_one_user_subject(session: AsyncSession, applet_one: AppletFull, tom: User, user: User) -> Subject:
    return await SubjectsService(session, tom.id).create(
        SubjectCreate(
            applet_id=applet_one.id,
            creator_id=user.id,
            first_name="Shell",
            last_name="Account",
            nickname="shell-account-user-0",
            secret_user_id=f"{uuid.uuid4()}",
        )
    )


@pytest.mark.usefixtures("mock_kiq_report")
class TestAnswerActivityItems(BaseTest):
    fixtures = [
        "workspaces/fixtures/workspaces.json",
    ]

    login_url = "/auth/login"
    answer_url = "/answers"
    public_answer_url = "/public/answers"

    review_activities_url = "/answers/applet/{applet_id}/review/activities"
    review_flows_url = "/answers/applet/{applet_id}/review/flows"

    summary_activities_url = "/answers/applet/{applet_id}/summary/activities"
    summary_activity_flows_url = "/answers/applet/{applet_id}/summary/flows"
    activity_identifiers_url = f"{summary_activities_url}/{{activity_id}}/identifiers"
    flow_identifiers_url = "/answers/applet/{applet_id}/flows/{flow_id}/identifiers"
    activity_versions_url = f"{summary_activities_url}/{{activity_id}}/versions"
    flow_versions_url = "/answers/applet/{applet_id}/flows/{flow_id}/versions"

    activity_answers_url = "/answers/applet/{applet_id}/activities/{activity_id}/answers"
    flow_submissions_url = "/answers/applet/{applet_id}/flows/{flow_id}/submissions"
    applet_submissions_list_url = "/answers/applet/{applet_id}/submissions"
    applet_answers_export_url = "/answers/applet/{applet_id}/data"
    applet_answers_completions_url = "/answers/applet/{applet_id}/completions"
    applets_answers_completions_url = "/answers/applet/completions"
    applet_submit_dates_url = "/answers/applet/{applet_id}/dates"

    activity_answer_url = "/answers/applet/{applet_id}/activities/{activity_id}/answers/{answer_id}"
    flow_submission_url = f"{flow_submissions_url}/{{submit_id}}"
    assessment_answers_url = "/answers/applet/{applet_id}/answers/{answer_id}/assessment"

    assessment_submissions_url = "/answers/applet/{applet_id}/submissions/{submission_id}/assessments"
    assessment_submissions_retrieve_url = "/answers/applet/{applet_id}/submissions/{submission_id}/assessments"
    assessment_submission_delete_url = (
        "/answers/applet/{applet_id}/submissions/{submission_id}/assessments/{assessment_id}"
    )
    submission_reviews_url = "/answers/applet/{applet_id}/submissions/{submission_id}/reviews"

    answer_reviews_url = "/answers/applet/{applet_id}/answers/{answer_id}/reviews"
    answer_notes_url = "/answers/applet/{applet_id}/answers/{answer_id}/activities/{activity_id}/notes"
    answer_note_detail_url = "/answers/applet/{applet_id}/answers/{answer_id}/activities/{activity_id}/notes/{note_id}"
    submission_notes_url = "/answers/applet/{applet_id}/submissions/{submission_id}/flows/{flow_id}/notes"
    submission_note_detail_url = (
        "/answers/applet/{applet_id}/submissions/{submission_id}/flows/{flow_id}/notes/{note_id}"
    )
    latest_activity_report_url = (
        "/answers/applet/{applet_id}/activities/{activity_id}/subjects/{subject_id}/latest_report"
    )
    latest_flow_report_url = "/answers/applet/{applet_id}/flows/{flow_id}/subjects/{subject_id}/latest_report"
    check_existence_url = "/answers/check-existence"
    assessment_delete_url = "/answers/applet/{applet_id}/answers/{answer_id}/assessment/{assessment_id}"
    multiinformat_assessment_validate_url = "/answers/applet/{applet_id}/multiinformant-assessment/validate"

    async def test_answer_activity_items_create_alert_for_respondent(
        self,
        mock_kiq_report: AsyncMock,
        tom: User,
        answer_with_alert_create: AppletAnswerCreate,
        tom_applet_subject: Subject,
        redis: RedisCacheTest,
        mailbox: TestMail,
        client: TestClient,
    ) -> None:
        client.login(tom)
        response = await client.post(self.answer_url, data=answer_with_alert_create)
        assert response.status_code == http.HTTPStatus.CREATED, response.json()

        mock_kiq_report.assert_awaited_once()

        published_values = await redis.get(f"channel_{tom.id}")
        published_values = published_values or []
        assert len(published_values) == 1
        assert len(redis._storage) == 1
        assert len(mailbox.mails) == 1
        assert mailbox.mails[0].subject == "Response alert"

    async def test_answer_activity_answer_dates_for_respondent(
        self,
        client: TestClient,
        tom: User,
        answer_with_alert_create: AppletAnswerCreate,
        tom_answer_on_applet_with_alert: AnswerSchema,
        tom_applet_subject: Subject,
    ):
        client.login(tom)
        response = await client.get(
            self.review_activities_url.format(applet_id=str(answer_with_alert_create.applet_id)),
            dict(
                targetSubjectId=tom_applet_subject.id,
                createdDate=datetime.datetime.utcnow().date(),
            ),
        )
        assert response.status_code == http.HTTPStatus.OK, response.json()
        assert response.json()["count"] == 1
        assert len(response.json()["result"][0]["answerDates"]) == 1

        answer_id = response.json()["result"][0]["answerDates"][0]["answerId"]
        response = await client.get(
            self.assessment_answers_url.format(
                applet_id=str(answer_with_alert_create.applet_id),
                answer_id=answer_id,
            )
        )
        assert response.status_code == http.HTTPStatus.OK, response.json()

    async def test_answer_activity_with_input_subject(
        self,
        client: TestClient,
        tom: User,
        answer_create_applet_one: AppletAnswerCreate,
        applet_one: AppletFull,
        applet_one_lucy_subject: Subject,
        applet_one_user_subject: Subject,
    ):
        client.login(tom)
        data = answer_create_applet_one.copy(deep=True)
        data.input_subject_id = applet_one_lucy_subject.id
        data.target_subject_id = applet_one_user_subject.id
        data.source_subject_id = applet_one_user_subject.id

        response = await client.post(self.answer_url, data=data)
        assert response.status_code == http.HTTPStatus.CREATED
        # TODO: check the response
        #  (there is no endpoint returning target_subject_id, source_subject_id, input_subject_id for an answer)

    async def test_create_answer__wrong_applet_version(
        self,
        client: TestClient,
        tom: User,
        answer_create: AppletAnswerCreate,
    ):
        client.login(tom)
        data = answer_create.copy(deep=True)
        data.version = "0.0.0"
        response = await client.post(self.answer_url, data=data)
        assert response.status_code == http.HTTPStatus.BAD_REQUEST
        assert response.json()["result"][0]["message"] == InvalidVersionError.message

    async def test_create_activity_answers__submit_duplicate(
        self,
        client: TestClient,
        tom: User,
        answer_create: AppletAnswerCreate,
    ):
        client.login(tom)
        data = answer_create.copy(deep=True)
        response = await client.post(self.answer_url, data=data)
        assert response.status_code == http.HTTPStatus.CREATED

        response = await client.post(self.answer_url, data=data)
        assert response.status_code == http.HTTPStatus.BAD_REQUEST

        data.submit_id = uuid.uuid4()
        response = await client.post(self.answer_url, data=data)
        assert response.status_code == http.HTTPStatus.CREATED

    async def test_create_activity_answer_flow_answer__submit_duplicate(
        self,
        client: TestClient,
        tom: User,
        answer_create: AppletAnswerCreate,
        applet_with_flow: AppletFull,
    ):
        client.login(tom)
        data: AppletAnswerCreate = answer_create.copy(deep=True)
        data.submit_id = uuid.uuid4()
        data.applet_id = applet_with_flow.id
        data.activity_id = applet_with_flow.activities[0].id
        data.flow_id = None

        response = await client.post(self.answer_url, data=data)
        assert response.status_code == http.HTTPStatus.CREATED

        data.flow_id = applet_with_flow.activity_flows[0].id
        response = await client.post(self.answer_url, data=data)
        assert response.status_code == http.HTTPStatus.BAD_REQUEST

        data.submit_id = uuid.uuid4()
        response = await client.post(self.answer_url, data=data)
        assert response.status_code == http.HTTPStatus.CREATED

    async def test_create_flow_answer__submit_duplicate(
        self,
        client: TestClient,
        tom: User,
        answer_create: AppletAnswerCreate,
        applet_with_flow: AppletFull,
    ):
        client.login(tom)
        data: AppletAnswerCreate = answer_create.copy(deep=True)
        data.submit_id = uuid.uuid4()
        data.applet_id = applet_with_flow.id
        data.flow_id = applet_with_flow.activity_flows[0].id
        data.activity_id = applet_with_flow.activity_flows[0].items[0].activity_id

        response = await client.post(self.answer_url, data=data)
        assert response.status_code == http.HTTPStatus.CREATED

        response = await client.post(self.answer_url, data=data)
        assert response.status_code == http.HTTPStatus.BAD_REQUEST

    async def test_create_flow_answer__submit_autocomplete(
        self,
        client: TestClient,
        tom: User,
        answer_create: AppletAnswerCreate,
        applet_with_flow: AppletFull,
    ):
        client.login(tom)
        data: AppletAnswerCreate = answer_create.copy(deep=True)
        data.submit_id = uuid.uuid4()
        data.applet_id = applet_with_flow.id
        data.flow_id = applet_with_flow.activity_flows[1].id
        data.activity_id = applet_with_flow.activity_flows[1].items[0].activity_id

        response = await client.post(self.answer_url, data=data)
        assert response.status_code == http.HTTPStatus.CREATED

        data.activity_id = applet_with_flow.activity_flows[1].items[2].activity_id
        data.is_flow_completed = True
        response = await client.post(self.answer_url, data=data)
        assert response.status_code == http.HTTPStatus.CREATED

        response = await client.post(self.answer_url, data=data)
        assert response.status_code == http.HTTPStatus.BAD_REQUEST

    async def test_create_flow_duplicate_activities_answer__submit(
        self,
        client: TestClient,
        tom: User,
        answer_create: AppletAnswerCreate,
        applet_with_flow_duplicated_activities: AppletFull,
    ):
        client.login(tom)
        data: AppletAnswerCreate = answer_create.copy(deep=True)
        data.submit_id = uuid.uuid4()
        data.applet_id = applet_with_flow_duplicated_activities.id
        data.flow_id = applet_with_flow_duplicated_activities.activity_flows[0].id
        data.activity_id = applet_with_flow_duplicated_activities.activity_flows[0].items[0].activity_id

        response = await client.post(self.answer_url, data=data)
        assert response.status_code == http.HTTPStatus.CREATED

        data.activity_id = applet_with_flow_duplicated_activities.activity_flows[0].items[1].activity_id
        response = await client.post(self.answer_url, data=data)
        assert response.status_code == http.HTTPStatus.CREATED

    async def test_create_flow_answer__correct_order(
        self,
        client: TestClient,
        tom: User,
        answer_create: AppletAnswerCreate,
        applet_with_flow: AppletFull,
    ):
        client.login(tom)
        data: AppletAnswerCreate = answer_create.copy(deep=True)
        data.submit_id = uuid.uuid4()
        data.applet_id = applet_with_flow.id
        data.flow_id = applet_with_flow.activity_flows[1].id
        data.activity_id = applet_with_flow.activity_flows[1].items[0].activity_id

        response = await client.post(self.answer_url, data=data)
        assert response.status_code == http.HTTPStatus.CREATED

        data.activity_id = applet_with_flow.activity_flows[1].items[1].activity_id

        response = await client.post(self.answer_url, data=data)
        assert response.status_code == http.HTTPStatus.CREATED

    async def test_create_flow_answer__wrong_order(
        self,
        client: TestClient,
        tom: User,
        answer_create: AppletAnswerCreate,
        applet_with_flow: AppletFull,
    ):
        client.login(tom)
        data: AppletAnswerCreate = answer_create.copy(deep=True)
        data.submit_id = uuid.uuid4()
        data.applet_id = applet_with_flow.id
        data.flow_id = applet_with_flow.activity_flows[1].id
        data.activity_id = applet_with_flow.activity_flows[1].items[1].activity_id

        response = await client.post(self.answer_url, data=data)
        assert response.status_code == http.HTTPStatus.BAD_REQUEST

        # different submit_id for second activity
        data.activity_id = applet_with_flow.activity_flows[1].items[0].activity_id

        response = await client.post(self.answer_url, data=data)
        assert response.status_code == http.HTTPStatus.CREATED

        data.submit_id = uuid.uuid4()
        data.activity_id = applet_with_flow.activity_flows[1].items[1].activity_id

        response = await client.post(self.answer_url, data=data)
        assert response.status_code == http.HTTPStatus.BAD_REQUEST

    @pytest.mark.usefixtures("mock_report_server_response", "answer")
    async def test_get_latest_summary(
        self, client: TestClient, tom: User, applet: AppletFull, tom_applet_subject: Subject
    ):
        client.login(tom)

        response = await client.post(
            self.latest_activity_report_url.format(
                applet_id=str(applet.id),
                activity_id=str(applet.activities[0].id),
                subject_id=str(tom_applet_subject.id),
            ),
        )
        assert response.status_code == http.HTTPStatus.OK
        assert response.content == b"pdf body"

    async def test_public_answer_activity_items_create_for_respondent(
        self, client: TestClient, public_answer_create: AppletAnswerCreate
    ):
        response = await client.post(self.public_answer_url, data=public_answer_create)
        assert response.status_code == http.HTTPStatus.CREATED

    async def test_answer_skippable_activity_items_create_for_respondent(
        self, client: TestClient, tom: User, answer_create: AppletAnswerCreate, applet: AppletFull
    ):
        client.login(tom)

        response = await client.post(self.answer_url, data=answer_create)

        assert response.status_code == http.HTTPStatus.CREATED, response.json()

        response = await client.get(
            self.applet_submit_dates_url.format(applet_id=str(applet.id)),
            dict(
                respondentId=tom.id,
                fromDate=datetime.date.today() - datetime.timedelta(days=10),
                toDate=datetime.date.today() + datetime.timedelta(days=10),
            ),
        )
        assert response.status_code == http.HTTPStatus.OK
        assert len(response.json()["result"]["dates"]) == 1

    async def test_list_submit_dates(
        self, client: TestClient, tom: User, answer_create: AppletAnswerCreate, applet: AppletFull
    ):
        client.login(tom)

        response = await client.post(self.answer_url, data=answer_create)
        assert response.status_code == http.HTTPStatus.CREATED

        response = await client.get(
            self.applet_submit_dates_url.format(applet_id=str(applet.id)),
            dict(
                respondentId=tom.id,
                fromDate=datetime.date.today() - datetime.timedelta(days=10),
                toDate=datetime.date.today() + datetime.timedelta(days=10),
            ),
        )
        assert response.status_code == http.HTTPStatus.OK
        assert len(response.json()["result"]["dates"]) == 1

    async def test_answer_flow_items_create_for_respondent(
        self, client: TestClient, tom: User, answer_create: AppletAnswerCreate
    ):
        client.login(tom)

        response = await client.post(self.answer_url, data=answer_create)

        assert response.status_code == http.HTTPStatus.CREATED

    async def test_answer_get_export_data__answer_from_manager(
        self,
        client: TestClient,
        tom: User,
        lucy: User,
        answer_create: AppletAnswerCreate,
        applet_one_lucy_manager: AppletFull,
        applet_one_lucy_respondent: AppletFull,
    ):
        client.login(lucy)
        data = answer_create.copy(deep=True)
        data.applet_id = applet_one_lucy_manager.id
        data.version = applet_one_lucy_manager.version
        data.activity_id = applet_one_lucy_manager.activities[0].id
        data.flow_id = None
        data.answer.item_ids = [i.id for i in applet_one_lucy_manager.activities[0].items]
        response = await client.post(self.answer_url, data=data)
        assert response.status_code == http.HTTPStatus.CREATED

        client.login(tom)
        response = await client.get(
            self.applet_answers_export_url.format(applet_id=str(applet_one_lucy_manager.id)),
        )
        assert response.status_code == http.HTTPStatus.OK
        assert re.match(
            r"\[admin account\] \([0-9a-f]{8}\-[0-9a-f]{4}\-4[0-9a-f]{3}\-[89ab][0-9a-f]{3}\-[0-9a-f]{12}\)",
            response.json()["result"]["answers"][0]["respondentSecretId"],
        )

    async def test_answer_activity_items_create_temporary_relation_success(
        self,
        tom: User,
        answer_create_applet_one: AppletAnswerCreate,
        client: TestClient,
        session: AsyncSession,
        sam: User,
        applet_one: AppletFull,
        applet_one_sam_respondent,
        applet_one_sam_subject,
    ) -> None:
        client.login(tom)
        subject_service = SubjectsService(session, tom.id)

        data = answer_create_applet_one.copy(deep=True)

        client.login(sam)
        subject_service = SubjectsService(session, sam.id)
        source_subject = await subject_service.create(
            SubjectCreate(
                applet_id=applet_one.id,
                creator_id=tom.id,
                first_name="source",
                last_name="subject",
                secret_user_id=f"{uuid.uuid4()}",
            )
        )
        target_subject = await subject_service.create(
            SubjectCreate(
                applet_id=applet_one.id,
                creator_id=tom.id,
                first_name="target",
                last_name="subject",
                secret_user_id=f"{uuid.uuid4()}",
            )
        )
        # create a relation between respondent and source
        await subject_service.create_relation(
            relation="take-now",
            source_subject_id=applet_one_sam_subject.id,
            subject_id=source_subject.id,
            meta={
                "expiresAt": (datetime.datetime.now() + datetime.timedelta(days=1)).isoformat(),
            },
        )
        # create a relation between respondent and target
        await subject_service.create_relation(
            relation="take-now",
            source_subject_id=applet_one_sam_subject.id,
            subject_id=target_subject.id,
            meta={
                "expiresAt": (datetime.datetime.now() + datetime.timedelta(days=1)).isoformat(),
            },
        )

        await subject_service.create_relation(
            relation="take-now",
            source_subject_id=source_subject.id,
            subject_id=target_subject.id,
            meta={
                "expiresAt": (datetime.datetime.now() + datetime.timedelta(days=1)).isoformat(),
            },
        )

        data.source_subject_id = source_subject.id
        data.target_subject_id = target_subject.id
        data.input_subject_id = applet_one_sam_subject.id

        # before posting the request, make sure that there is a temporary relation
        existing_relation = await subject_service.get_relation(applet_one_sam_subject.id, target_subject.id)
        assert existing_relation

        response = await client.post(self.answer_url, data=data)

        assert response.status_code == http.HTTPStatus.CREATED, response.json()
        # after submitting make sure that the relation has been deleted
        relation_exists = await subject_service.get_relation(applet_one_sam_subject.id, target_subject.id)
        assert not relation_exists

    async def test_answer_activity_items_relation_equal_other_when_relation_is_temp(
        self,
        tom: User,
        answer_create_applet_one: AppletAnswerCreate,
        client: TestClient,
        session: AsyncSession,
        sam: User,
        applet_one: AppletFull,
        applet_one_sam_respondent,
        applet_one_sam_subject,
    ) -> None:
        client.login(tom)
        subject_service = SubjectsService(session, tom.id)

        data = answer_create_applet_one.copy(deep=True)

        client.login(sam)
        subject_service = SubjectsService(session, sam.id)
        target_subject = await subject_service.create(
            SubjectCreate(
                applet_id=applet_one.id,
                creator_id=tom.id,
                first_name="target",
                last_name="subject",
                secret_user_id=f"{uuid.uuid4()}",
            )
        )
        await subject_service.create_relation(
            relation="take-now",
            source_subject_id=applet_one_sam_subject.id,
            subject_id=target_subject.id,
            meta={
                "expiresAt": (datetime.datetime.now() + datetime.timedelta(days=1)).isoformat(),
            },
        )

        data.source_subject_id = applet_one_sam_subject.id
        data.target_subject_id = target_subject.id
        data.input_subject_id = applet_one_sam_subject.id

        response = await client.post(self.answer_url, data=data)

        assert response.status_code == http.HTTPStatus.CREATED, response.json()

        answers, _ = await AnswersCRUD(session).get_applet_answers(applet_id=applet_one.id, page=1, limit=5)

        assert answers[0].relation == Relation.other

    async def test_answer_activity_items_relation_equal_other_when_relation_is_permanent(
        self,
        tom: User,
        answer_create_applet_one: AppletAnswerCreate,
        client: TestClient,
        session: AsyncSession,
        sam: User,
        applet_one: AppletFull,
        applet_one_sam_respondent,
        applet_one_sam_subject,
    ) -> None:
        client.login(tom)
        subject_service = SubjectsService(session, tom.id)

        data = answer_create_applet_one.copy(deep=True)

        client.login(sam)
        subject_service = SubjectsService(session, sam.id)
        target_subject = await subject_service.create(
            SubjectCreate(
                applet_id=applet_one.id,
                creator_id=tom.id,
                first_name="target",
                last_name="subject",
                secret_user_id=f"{uuid.uuid4()}",
            )
        )
        await subject_service.create_relation(
            relation="father",
            source_subject_id=applet_one_sam_subject.id,
            subject_id=target_subject.id,
        )

        data.source_subject_id = applet_one_sam_subject.id
        data.target_subject_id = target_subject.id
        data.input_subject_id = applet_one_sam_subject.id

        response = await client.post(self.answer_url, data=data)

        assert response.status_code == http.HTTPStatus.CREATED, response.json()

        answers, _ = await AnswersCRUD(session).get_applet_answers(applet_id=applet_one.id, page=1, limit=5)

        assert answers[0].relation == "father"

    async def test_answer_activity_items_create_permanent_relation_success(
        self,
        tom: User,
        answer_create_applet_one: AppletAnswerCreate,
        client: TestClient,
        session: AsyncSession,
        sam: User,
        applet_one: AppletFull,
        applet_one_sam_respondent,
        applet_one_sam_subject,
    ) -> None:
        client.login(tom)
        subject_service = SubjectsService(session, tom.id)

        data = answer_create_applet_one.copy(deep=True)

        client.login(sam)
        subject_service = SubjectsService(session, sam.id)
        source_subject = await subject_service.create(
            SubjectCreate(
                applet_id=applet_one.id,
                creator_id=tom.id,
                first_name="source",
                last_name="subject",
                secret_user_id=f"{uuid.uuid4()}",
            )
        )
        target_subject = await subject_service.create(
            SubjectCreate(
                applet_id=applet_one.id,
                creator_id=tom.id,
                first_name="target",
                last_name="subject",
                secret_user_id=f"{uuid.uuid4()}",
            )
        )
        # create a relation between respondent and source
        await subject_service.create_relation(
            relation="parent", source_subject_id=applet_one_sam_subject.id, subject_id=source_subject.id
        )
        # create a relation between respondent and target
        await subject_service.create_relation(
            relation="parent", source_subject_id=applet_one_sam_subject.id, subject_id=target_subject.id
        )

        await subject_service.create_relation(
            relation="parent", source_subject_id=source_subject.id, subject_id=target_subject.id
        )

        data.source_subject_id = source_subject.id
        data.target_subject_id = target_subject.id
        data.input_subject_id = applet_one_sam_subject.id

        # before posting the request, make sure that there is a temporary relation
        existing_relation = await subject_service.get_relation(applet_one_sam_subject.id, target_subject.id)
        assert existing_relation

        response = await client.post(self.answer_url, data=data)

        assert response.status_code == http.HTTPStatus.CREATED, response.json()
        # after submitting make sure that the relation has not been deleted
        relation_exists = await subject_service.get_relation(applet_one_sam_subject.id, target_subject.id)
        assert relation_exists

    async def test_answer_activity_items_create_expired_temporary_relation_fail(
        self,
        tom: User,
        answer_create_applet_one: AppletAnswerCreate,
        client: TestClient,
        session: AsyncSession,
        sam: User,
        applet_one: AppletFull,
        applet_one_sam_respondent,
        applet_one_sam_subject,
    ) -> None:
        client.login(tom)
        subject_service = SubjectsService(session, tom.id)

        data = answer_create_applet_one.copy(deep=True)

        client.login(sam)
        subject_service = SubjectsService(session, sam.id)
        source_subject = await subject_service.create(
            SubjectCreate(
                applet_id=applet_one.id,
                creator_id=tom.id,
                first_name="source",
                last_name="subject",
                secret_user_id=f"{uuid.uuid4()}",
            )
        )
        target_subject = await subject_service.create(
            SubjectCreate(
                applet_id=applet_one.id,
                creator_id=tom.id,
                first_name="target",
                last_name="subject",
                secret_user_id=f"{uuid.uuid4()}",
            )
        )
        # create a relation between respondent and source
        await subject_service.create_relation(
            relation="take-now",
            source_subject_id=applet_one_sam_subject.id,
            subject_id=source_subject.id,
            meta={
                "expiresAt": (datetime.datetime.now() - datetime.timedelta(days=1)).isoformat(),
            },
        )
        # create a relation between respondent and target
        await subject_service.create_relation(
            relation="take-now",
            source_subject_id=applet_one_sam_subject.id,
            subject_id=target_subject.id,
            meta={
                "expiresAt": (datetime.datetime.now() - datetime.timedelta(days=1)).isoformat(),
            },
        )

        await subject_service.create_relation(
            relation="take-now",
            source_subject_id=source_subject.id,
            subject_id=target_subject.id,
            meta={
                "expiresAt": (datetime.datetime.now() - datetime.timedelta(days=1)).isoformat(),
            },
        )

        data.source_subject_id = source_subject.id
        data.target_subject_id = target_subject.id
        data.input_subject_id = applet_one_sam_subject.id

        # before posting the request, make sure that there is a temporary relation
        existing_relation = await subject_service.get_relation(applet_one_sam_subject.id, target_subject.id)
        assert existing_relation

        response = await client.post(self.answer_url, data=data)
        assert response.status_code == http.HTTPStatus.BAD_REQUEST, response.json()

    async def test_answer_get_export_data__answer_from_respondent(
        self,
        client: TestClient,
        tom: User,
        lucy: User,
        answer_create: AppletAnswerCreate,
        applet_one_lucy_respondent: AppletFull,
    ):
        client.login(lucy)
        data = answer_create.copy(deep=True)
        data.applet_id = applet_one_lucy_respondent.id
        data.version = applet_one_lucy_respondent.version
        data.activity_id = applet_one_lucy_respondent.activities[0].id
        data.flow_id = None
        data.answer.item_ids = [i.id for i in applet_one_lucy_respondent.activities[0].items]
        response = await client.post(self.answer_url, data=data)
        assert response.status_code == http.HTTPStatus.CREATED

        client.login(tom)
        response = await client.get(
            self.applet_answers_export_url.format(applet_id=str(applet_one_lucy_respondent.id)),
        )
        assert response.status_code == http.HTTPStatus.OK
        secret_user_id = response.json()["result"]["answers"][0]["respondentSecretId"]
        assert secret_user_id != f"[admin account] ({lucy.email_encrypted})"
        assert uuid.UUID(secret_user_id)

    async def test_answer_get_export_data__only_last_activity(
        self,
        client: TestClient,
        tom: User,
        answer_create: AppletAnswerCreate,
        applet: AppletFull,
        applet_with_additional_item: AppletFull,  # next version of applet
    ):
        client.login(tom)
        response = await client.post(self.answer_url, data=answer_create)
        assert response.status_code == http.HTTPStatus.CREATED

        response = await client.get(
            self.applet_answers_export_url.format(applet_id=str(applet.id)), query={"activitiesLastVersion": True}
        )
        assert response.status_code == http.HTTPStatus.OK
        assert response.json()["result"]["activities"][0]["id"] == str(applet_with_additional_item.activities[0].id)
        assert response.json()["result"]["activities"][0]["version"] == applet_with_additional_item.version
        assert (
            response.json()["result"]["activities"][0]["idVersion"]
            == f"{applet_with_additional_item.activities[0].id}_{applet_with_additional_item.version}"
        )

    async def test_answer_with_skipping_all(
        self,
        client: TestClient,
        tom: User,
        answer_create: AppletAnswerCreate,
    ):
        client.login(tom)
        response = await client.post(self.answer_url, data=answer_create)

        assert response.status_code == http.HTTPStatus.CREATED, response.json()

    async def test_answered_applet_activities_1(
        self,
        client: TestClient,
        tom: User,
        tom_answer: AnswerSchema,
        answer_create: AppletAnswerCreate,
        tom_applet_subject: Subject,
        session: AsyncSession,
    ):
        client.login(tom)
        response = await client.get(
            self.review_activities_url.format(applet_id=str(tom_answer.applet_id)),
            dict(
                targetSubjectId=tom_applet_subject.id,
                createdDate=datetime.datetime.utcnow().date(),
            ),
        )

        assert response.status_code == http.HTTPStatus.OK
        assert response.json()["count"] == 1
        assert len(response.json()["result"][0]["answerDates"]) == 1

        activity_id = tom_answer.activity_history_id.split("_")[0]
        answer_id = response.json()["result"][0]["answerDates"][0]["answerId"]
        response = await client.get(
            self.activity_answer_url.format(
                applet_id=str(tom_answer.applet_id),
                answer_id=answer_id,
                activity_id=activity_id,
            )
        )

        assert response.status_code == http.HTTPStatus.OK
        data = response.json()["result"]
        assert data["answer"]["events"] == answer_create.answer.events
        assert set(data["summary"]["identifier"]) == {"lastAnswerDate", "identifier", "userPublicKey"}
        assert data["summary"]["identifier"]["identifier"] == "encrypted_identifier"

    async def test_get_answer_activity(self, client: TestClient, tom: User, applet: AppletFull, answer: AnswerSchema):
        client.login(tom)
        response = await client.get(
            self.activity_answer_url.format(
                applet_id=str(applet.id),
                answer_id=answer.id,
                activity_id=applet.activities[0].id,
            )
        )
        assert response.status_code == http.HTTPStatus.OK  # TODO: Check response

    async def test_fail_answered_applet_not_existed_activities(
        self, client: TestClient, tom: User, applet: AppletFull, uuid_zero: uuid.UUID, answer: AnswerSchema
    ):
        client.login(tom)
        response = await client.get(
            self.activity_answer_url.format(
                applet_id=str(applet.id),
                answer_id=answer.id,
                activity_id=uuid_zero,
            )
        )
        assert response.status_code == http.HTTPStatus.NOT_FOUND

    async def test_applet_activity_answers(
        self, client: TestClient, tom: User, applet: AppletFull, answer: AnswerSchema
    ):
        client.login(tom)
        response = await client.get(
            self.activity_answers_url.format(
                applet_id=str(applet.id),
                activity_id=str(applet.activities[0].id),
            ),
        )

        assert response.status_code == http.HTTPStatus.OK, response.json()
        assert response.json()["count"] == 1

    async def test_applet_assessment_retrieve(
        self, client: TestClient, tom: User, answer_reviewable_activity: AnswerSchema
    ):
        client.login(tom)
        response = await client.get(
            self.assessment_answers_url.format(
                applet_id=str(answer_reviewable_activity.applet_id),
                answer_id=answer_reviewable_activity.id,
            )
        )

        assert response.status_code == http.HTTPStatus.OK
        assert response.json()["result"]

    async def test_applet_assessment_create(
        self,
        client: TestClient,
        tom: User,
        assessment_create: AssessmentAnswerCreate,
        answer_reviewable_activity: AnswerSchema,
        applet_with_reviewable_activity: AppletFull,
    ):
        client.login(tom)

        response = await client.post(
            self.assessment_answers_url.format(
                applet_id=str(answer_reviewable_activity.applet_id),
                answer_id=answer_reviewable_activity.id,
            ),
            data=assessment_create,
        )

        assert response.status_code == http.HTTPStatus.CREATED
        review_activity = next(i for i in applet_with_reviewable_activity.activities if i.is_reviewable)
        general_activity = next(i for i in applet_with_reviewable_activity.activities if not i.is_reviewable)

        response = await client.get(
            self.assessment_answers_url.format(
                applet_id=str(answer_reviewable_activity.applet_id),
                answer_id=answer_reviewable_activity.id,
            )
        )
        assert response.status_code == http.HTTPStatus.OK
        assessment = response.json()["result"]
        assert assessment["answer"] == assessment_create.answer
        assert assessment["reviewerPublicKey"] == assessment_create.reviewer_public_key
        assert assessment["itemIds"] == [str(i) for i in assessment_create.item_ids]
        assert assessment["versions"] == [
            f"{general_activity.id}_{applet_with_reviewable_activity.version}",
            f"{review_activity.id}_{applet_with_reviewable_activity.version}",
        ]
        assert not assessment["itemsLast"] == general_activity.dict()["items"][0]
        assert not assessment["items"]

    @pytest.mark.usefixtures("assessment")
    async def test_get_review_assessment(
        self,
        client: TestClient,
        tom: User,
        answer_reviewable_activity: AnswerSchema,
        assessment_create: AssessmentAnswerCreate,
    ):
        client.login(tom)
        response = await client.get(
            self.answer_reviews_url.format(
                applet_id=str(answer_reviewable_activity.applet_id),
                answer_id=answer_reviewable_activity.id,
            )
        )
        assert response.status_code == http.HTTPStatus.OK
        assert set(response.json()["result"][0].keys()) == {
            "answer",
            "createdAt",
            "updatedAt",
            "id",
            "itemIds",
            "items",
            "reviewer",
            "reviewerPublicKey",
        }
        assert response.json()["count"] == 1
        review = response.json()["result"][0]
        assert review["answer"] == assessment_create.answer
        assert review["reviewerPublicKey"] == assessment_create.reviewer_public_key
        assert review["itemIds"] == [str(i) for i in assessment_create.item_ids]
        assert review["reviewer"]["firstName"] == tom.first_name
        assert review["reviewer"]["lastName"] == tom.last_name

    async def test_applet_activities(self, client: TestClient, tom: User, answer: AnswerSchema, tom_applet_subject):
        client.login(tom)

        response = await client.get(
            self.review_activities_url.format(applet_id=str(answer.applet_id)),
            dict(
                targetSubjectId=tom_applet_subject.id,
                createdDate=datetime.datetime.utcnow().date(),
            ),
        )

        assert response.status_code == http.HTTPStatus.OK, response.json()
        assert response.json()["count"] == 1
        assert len(response.json()["result"][0]["answerDates"]) == 1

    async def test_add_note(self, client: TestClient, tom: User, answer: AnswerSchema, note_create_data: AnswerNote):
        client.login(tom)

        response = await client.post(self.answer_notes_url.format(**note_url_path_data(answer)), data=note_create_data)

        assert response.status_code == http.HTTPStatus.CREATED, response.json()

        response = await client.get(self.answer_notes_url.format(**note_url_path_data(answer)))

        assert response.status_code == http.HTTPStatus.OK, response.json()
        assert response.json()["count"] == 1
        note = response.json()["result"][0]
        assert note["note"] == note_create_data.note
        assert note["user"]["firstName"] == tom.first_name
        assert note["user"]["lastName"] == tom.last_name
        assert note["user"]["id"] == str(tom.id)
        # Just check that other columns in place
        assert note["id"]
        assert note["createdAt"]

    async def test_edit_note(self, client: TestClient, tom: User, answer: AnswerSchema, answer_note: AnswerNoteSchema):
        client.login(tom)

        note_new = answer_note.note + "new"

        response = await client.put(
            self.answer_note_detail_url.format(**note_url_path_data(answer), note_id=answer_note.id),
            dict(note=note_new),
        )
        assert response.status_code == http.HTTPStatus.OK

        response = await client.get(self.answer_notes_url.format(**note_url_path_data(answer)))

        assert response.status_code == http.HTTPStatus.OK, response.json()
        assert response.json()["count"] == 1
        assert response.json()["result"][0]["note"] == note_new

    async def test_delete_note(
        self, client: TestClient, tom: User, answer: AnswerSchema, answer_note: AnswerNoteSchema
    ):
        client.login(tom)
        note_id = answer_note.id

        response = await client.delete(
            self.answer_note_detail_url.format(**note_url_path_data(answer), note_id=note_id)
        )
        assert response.status_code == http.HTTPStatus.NO_CONTENT

        response = await client.get(self.answer_notes_url.format(**note_url_path_data(answer)))
        assert response.status_code == http.HTTPStatus.OK
        assert response.json()["count"] == 0

    async def test_answer_activity_items_create_for_not_respondent(
        self, client: TestClient, user: User, answer_create: AppletAnswerCreate
    ):
        client.login(user)
        response = await client.post(self.answer_url, data=answer_create)
        assert response.status_code == http.HTTPStatus.FORBIDDEN

    @pytest.mark.usefixtures("assessment")
    async def test_answers_export(
        self,
        client: TestClient,
        tom: User,
        answer_reviewable_activity_with_ts_offset: AnswerSchema,
        answer_reviewable_activity_with_tz_offset_create: AppletAnswerCreate,
    ):
        client.login(tom)
        response = await client.get(
            self.applet_answers_export_url.format(
                applet_id=str(answer_reviewable_activity_with_ts_offset.applet_id),
            )
        )

        assert response.status_code == http.HTTPStatus.OK
        resp_data = response.json()
        data = resp_data["result"]
        assert set(data.keys()) == {"answers", "activities"}
        # One answer, one answer with ts offset, one assessment
        assert len(data["answers"]) == 3
        assert resp_data["count"] == 3
        assessment = next(i for i in data["answers"] if i["reviewedAnswerId"] is not None)
        answer_with_tz = next(i for i in data["answers"] if i["tzOffset"] is not None)
        answer_for_review = next(i for i in data["answers"] if i["id"] == assessment["reviewedAnswerId"])
        # fmt: off
        expected_keys = {
            "activityHistoryId", "activityId", "answer", "appletHistoryId",
            "appletId", "createdAt", "events", "flowHistoryId", "flowId",
            "flowName", "id", "itemIds", "migratedData", "respondentId",
            "respondentSecretId", "reviewedAnswerId", "userPublicKey",
            "version", "submitId", "scheduledDatetime", "startDatetime",
            "endDatetime", "legacyProfileId", "migratedDate",
            "relation", "sourceSubjectId", "sourceSecretId", "targetSubjectId",
            "targetSecretId", "client", "tzOffset", "scheduledEventId", "reviewedFlowSubmitId"
        }
        # Comment for now, wtf is it
        # assert int(answer['startDatetime'] * 1000) == answer_item_create.start_time
        # fmt: on
        answer_reviewable_activity_with_tz_offset_create.answer.tz_offset = cast(
            int, answer_reviewable_activity_with_tz_offset_create.answer.tz_offset
        )
        assert answer_with_tz["tzOffset"] == answer_reviewable_activity_with_tz_offset_create.answer.tz_offset
        assert set(assessment.keys()) == expected_keys
        assert assessment["reviewedAnswerId"] == answer_for_review["id"]
        assert re.match(
            r"\[admin account\] \([0-9a-f]{8}\-[0-9a-f]{4}\-4[0-9a-f]{3}\-[89ab][0-9a-f]{3}\-[0-9a-f]{12}\)",
            answer_for_review["respondentSecretId"],
        )

    async def test_get_applet_answers_without_assessment(
        self, client: TestClient, tom: User, applet: AppletFull, answer_shell_account_target
    ):
        client.login(tom)
        response = await client.get(
            self.applet_answers_export_url.format(
                applet_id=str(applet.id),
            )
        )

        assert response.status_code == http.HTTPStatus.OK
        resp_data = response.json()
        data = resp_data["result"]
        assert len(data["answers"]) == 1
        assert resp_data["count"] == 1
        assert data["answers"][0]["respondentId"] == str(tom.id)
        assert data["answers"][0]["respondentSecretId"] == answer_shell_account_target["target_secret_user_id"]

    @pytest.mark.parametrize(
        "user_fixture, exp_cnt",
        (
            ("lucy", 0),
            ("tom", 1),  # Tom is respondent for the 'answer' fixture
        ),
    )
    async def test_get_applet_answers_export_filter_by_respondent_id(
        self,
        client: TestClient,
        tom: User,
        answer: AnswerSchema,
        request: FixtureRequest,
        user_fixture: str,
        exp_cnt: int,
    ):
        client.login(tom)
        respondent: User = request.getfixturevalue(user_fixture)
        response = await client.get(
            self.applet_answers_export_url.format(
                applet_id=str(answer.applet_id),
            ),
            dict(respondentIds=str(respondent.id)),
        )

        assert response.status_code == http.HTTPStatus.OK
        assert response.json()["count"] == exp_cnt
        assert len(response.json()["result"]["answers"]) == exp_cnt

    async def test_get_activity_identifiers(
        self, client: TestClient, tom: User, answer_create: AppletAnswerCreate, applet: AppletFull
    ):
        client.login(tom)
        identifier_url = self.activity_identifiers_url.format(
            applet_id=str(applet.id), activity_id=str(applet.activities[0].id)
        )
        identifier_url = f"{identifier_url}?respondentId={tom.id}"
        response = await client.get(identifier_url)
        assert response.status_code == http.HTTPStatus.OK
        assert response.json()["count"] == 0

        created_at = datetime.datetime.utcnow()
        data = answer_create.copy(deep=True)
        data.created_at = created_at

        response = await client.post(self.answer_url, data=data)
        assert response.status_code == http.HTTPStatus.CREATED

        response = await client.get(identifier_url)
        assert response.status_code == http.HTTPStatus.OK
        assert response.json()["count"] == 1
        assert response.json()["result"][0]["identifier"] == answer_create.answer.identifier
        assert response.json()["result"][0]["userPublicKey"] == answer_create.answer.user_public_key
        assert datetime.datetime.fromisoformat(response.json()["result"][0]["lastAnswerDate"]) == created_at

    async def test_get_flow_identifiers(
        self,
        mock_kiq_report,
        client,
        tom: User,
        applet_with_flow: AppletFull,
        applet_with_flow_answer_create: list[AppletAnswerCreate],
        tom_answer_activity_flow_multiple,
        session,
    ):
        applet = applet_with_flow
        answers = applet_with_flow_answer_create
        client.login(tom)

        tom_subject = await SubjectsService(session, tom.id).get_by_user_and_applet(tom.id, applet.id)
        assert tom_subject
        for flow in applet.activity_flows:
            flow_answers = [
                answer for answer in answers if answer.flow_id == flow.id and answer.answer.identifier is not None
            ]

            identifier_url = self.flow_identifiers_url.format(applet_id=applet.id, flow_id=flow.id)
            response = await client.get(identifier_url, dict(targetSubjectId=tom_subject.id))

            assert response.status_code == 200
            data = response.json()
            assert data["count"] == len(flow_answers)
            data = data["result"]
            for i, _answer in enumerate(flow_answers):
                assert set(data[i].keys()) == {"identifier", "userPublicKey", "lastAnswerDate"}
                assert data[i]["identifier"] == _answer.answer.identifier
                assert data[i]["userPublicKey"] == _answer.answer.user_public_key

    async def test_get_flow_identifiers_incomplete_submission(
        self,
        mock_kiq_report,
        client,
        tom: User,
        applet_with_flow: AppletFull,
        applet_with_flow_answer_create: list[AppletAnswerCreate],
        tom_answer_activity_flow_incomplete,
        session,
    ):
        applet = applet_with_flow
        client.login(tom)

        tom_subject = await SubjectsService(session, tom.id).get_by_user_and_applet(tom.id, applet.id)
        assert tom_subject

        identifier_url = self.flow_identifiers_url.format(
            applet_id=applet.id, flow_id=applet_with_flow.activity_flows[0].id
        )
        response = await client.get(identifier_url, dict(targetSubjectId=tom_subject.id))

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 0
        assert data["result"] == []

    # TODO: Move to another place, not needed any answer for test
    async def test_get_all_activity_versions_for_applet(self, client: TestClient, tom: User, applet: AppletFull):
        client.login(tom)

        response = await client.get(
            self.activity_versions_url.format(
                applet_id=str(applet.id),
                activity_id=str(applet.activities[0].id),
            )
        )

        assert response.status_code == http.HTTPStatus.OK
        assert response.json()["count"] == 1
        assert response.json()["result"][0]["version"] == applet.version
        assert response.json()["result"][0]["createdAt"]

    async def test_get_summary_activities_no_answer_no_performance_task(
        self, client: TestClient, tom: User, applet: AppletFull
    ):
        client.login(tom)

        response = await client.get(
            self.summary_activities_url.format(
                applet_id=str(applet.id),
            )
        )

        assert response.status_code == http.HTTPStatus.OK
        assert response.json()["count"] == 1
        assert response.json()["result"][0]["name"] == applet.activities[0].name
        assert response.json()["result"][0]["id"] == str(applet.activities[0].id)
        assert not response.json()["result"][0]["isPerformanceTask"]
        assert not response.json()["result"][0]["hasAnswer"]

    async def test_get_flow_versions(self, client, tom, applet_with_flow: AppletFull):
        client.login(tom)

        response = await client.get(
            self.flow_versions_url.format(
                applet_id=applet_with_flow.id,
                flow_id=applet_with_flow.activity_flows[0].id,
            )
        )

        assert response.status_code == 200
        assert response.json()["count"] == 1
        data = response.json()["result"]
        assert set(data[0].keys()) == {"version", "createdAt"}
        assert response.json()["result"][0]["version"] == applet_with_flow.version

    @pytest.mark.usefixtures("answer")
    async def test_get_summary_activities_has_answer_no_performance_task(
        self, client: TestClient, tom: User, applet: AppletFull, tom_applet_subject
    ):
        client.login(tom)

        response = await client.get(
            self.summary_activities_url.format(
                applet_id=str(applet.id),
            ),
            query={"targetSubjectId": tom_applet_subject.id},
        )

        assert response.status_code == http.HTTPStatus.OK
        assert response.json()["count"] == 1
        activity = response.json()["result"][0]
        assert activity["name"] == applet.activities[0].name
        assert activity["id"] == str(applet.activities[0].id)
        assert not activity["isPerformanceTask"]
        assert activity["hasAnswer"]

    async def test_get_summary_activities_performance_tasks_no_answers(
        self, client: TestClient, tom: User, applet_with_all_performance_tasks: AppletFull
    ):
        client.login(tom)

        response = await client.get(
            self.summary_activities_url.format(
                applet_id=str(applet_with_all_performance_tasks.id),
            )
        )

        assert response.status_code == http.HTTPStatus.OK
        assert response.json()["count"] == len(applet_with_all_performance_tasks.activities)
        applet_with_all_performance_tasks.activities.sort(key=lambda x: x.id)
        sorted_result = sorted(response.json()["result"], key=lambda x: x["id"])
        for exp, act in zip(applet_with_all_performance_tasks.activities, sorted_result):
            assert act["id"] == str(exp.id)
            assert act["name"] == exp.name
            assert act["isPerformanceTask"]
            assert not act["hasAnswer"]

    async def test_store_client_meta(
        self, client: TestClient, session: AsyncSession, tom: User, answer_create: AppletAnswerCreate
    ):
        client.login(tom)
        response = await client.post(self.answer_url, data=answer_create)
        assert response.status_code == http.HTTPStatus.CREATED

        db_result = await session.execute(select(AnswerSchema))
        res: AnswerSchema = db_result.scalars().first()
        assert res.client["app_id"] == answer_create.client.app_id
        assert res.client["app_version"] == answer_create.client.app_version
        assert res.client["width"] == answer_create.client.width
        assert res.client["height"] == answer_create.client.height

    async def test_activity_answers_by_identifier(
        self, client: TestClient, tom: User, answer: AnswerSchema, answer_create: AppletAnswerCreate
    ):
        client.login(tom)

        response = await client.get(
            self.activity_answers_url.format(
                applet_id=str(answer_create.applet_id),
                activity_id=str(answer_create.activity_id),
            ),
            query={"emptyIdentifiers": False, "identifiers": answer_create.answer.identifier},
        )

        assert response.status_code == http.HTTPStatus.OK
        result = response.json()
        assert result["count"] == 1
        assert result["result"][0]["answerId"] == str(answer.id)

    async def test_applet_completions(
        self, client: TestClient, tom: User, answer: AnswerSchema, answer_create: AppletAnswerCreate
    ):
        client.login(tom)
        answer_create.answer.local_end_date = cast(datetime.date, answer_create.answer.local_end_date)
        answer_create.answer.local_end_time = cast(datetime.time, answer_create.answer.local_end_time)
        response = await client.get(
            self.applet_answers_completions_url.format(
                applet_id=str(answer.applet_id),
            ),
            {"fromDate": answer_create.answer.local_end_date.isoformat(), "version": answer.version},
        )

        assert response.status_code == http.HTTPStatus.OK
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
            "targetSubjectId",
            "scheduledEventId",
            "localEndDate",
            "localEndTime",
        }
        assert activity_answer_data["answerId"] == str(answer.id)
        assert activity_answer_data["localEndTime"] == str(answer_create.answer.local_end_time)

    async def test_applets_completions(
        self, client: TestClient, tom: User, answer: AnswerSchema, answer_create: AppletAnswerCreate
    ):
        client.login(tom)
        answer_create.answer.local_end_date = cast(datetime.date, answer_create.answer.local_end_date)
        answer_create.answer.local_end_time = cast(datetime.time, answer_create.answer.local_end_time)
        # test completions
        response = await client.get(
            url=self.applets_answers_completions_url,
            query={"fromDate": answer_create.answer.local_end_date.isoformat()},
        )

        assert response.status_code == http.HTTPStatus.OK
        data = response.json()["result"]
        # 2 session applets and 1 for answers
        assert len(data) == 3
        applet_with_answer = next(i for i in data if i["id"] == str(answer.applet_id))

        assert applet_with_answer["id"] == str(answer.applet_id)
        assert applet_with_answer["version"] == answer.version
        assert len(applet_with_answer["activities"]) == 1
        activity_answer_data = applet_with_answer["activities"][0]
        assert set(activity_answer_data.keys()) == {
            "id",
            "answerId",
            "submitId",
            "targetSubjectId",
            "scheduledEventId",
            "localEndDate",
            "localEndTime",
        }
        assert activity_answer_data["answerId"] == str(answer.id)
        assert activity_answer_data["scheduledEventId"] == answer_create.answer.scheduled_event_id
        assert activity_answer_data["localEndDate"] == answer_create.answer.local_end_date.isoformat()
        assert activity_answer_data["localEndTime"] == str(answer_create.answer.local_end_time)
        for applet_data in data:
            if applet_data["id"] != str(answer.applet_id):
                assert not applet_data["activities"]
                assert not applet_data["activityFlows"]

    async def test_summary_restricted_for_reviewer_if_external_respondent(
        self, client: TestClient, user: User, user_reviewer_applet_one: AppletFull
    ):
        client.login(user)

        response = await client.get(self.summary_activities_url.format(applet_id=str(user_reviewer_applet_one.id)))

        assert response.status_code == http.HTTPStatus.FORBIDDEN

    async def test_public_answer_with_zero_start_time_end_time_timestamps(
        self, client: TestClient, public_answer_create: AppletAnswerCreate
    ):
        create_data = public_answer_create.dict()
        create_data["answer"]["start_time"] = 0
        create_data["answer"]["end_time"] = 0

        response = await client.post(self.public_answer_url, data=create_data)

        assert response.status_code == http.HTTPStatus.CREATED

    async def test_check_existence_answer_exists(self, client: TestClient, tom: User, answer: AnswerSchema):
        client.login(tom)
        data = {
            "applet_id": str(answer.applet_id),
            "activity_id": answer.activity_history_id.split("_")[0],
            # On backend we devide on 1000
            "created_at": answer.created_at.timestamp() * 1000,
        }
        resp = await client.post(self.check_existence_url, data=data)
        assert resp.status_code == http.HTTPStatus.OK
        assert resp.json()["result"]["exists"]

    @pytest.mark.parametrize(
        "column,value",
        (
            ("activity_id", "00000000-0000-0000-0000-000000000000_99"),
            ("created_at", datetime.datetime.utcnow().timestamp() * 1000),
        ),
    )
    async def test_check_existence_answer_does_not_exist(
        self, client: TestClient, tom: User, answer: AnswerSchema, column: str, value: str
    ):
        client.login(tom)
        data = {
            "applet_id": str(answer.applet_id),
            "activity_id": answer.activity_history_id.split("_")[0],
            "created_at": answer.created_at.timestamp(),
        }
        data[column] = value
        resp = await client.post(self.check_existence_url, data=data)
        assert resp.status_code == http.HTTPStatus.OK
        assert not resp.json()["result"]["exists"]

    async def test_check_existence_answer_does_not_exist__not_answer_applet(
        self, client: TestClient, tom: User, answer: AnswerSchema, applet_one: AppletFull
    ):
        client.login(tom)
        data = {
            "applet_id": str(applet_one.id),
            "activity_id": answer.activity_history_id.split("_")[0],
            "created_at": answer.created_at.timestamp(),
        }
        resp = await client.post(self.check_existence_url, data=data)
        assert resp.status_code == http.HTTPStatus.OK
        assert not resp.json()["result"]["exists"]

    @pytest.mark.usefixtures("applet_lucy_respondent")
    async def test_check_existence_answer_submit_same_time(
        self, client: TestClient, tom: User, answer: AnswerSchema, lucy: User
    ):
        client.login(tom)
        data = {
            "appletId": str(answer.applet_id),
            "activityId": answer.activity_history_id.split("_")[0],
            # On backend we devide on 1000
            "createdAt": answer.created_at.timestamp() * 1000,
            "submitId": str(answer.submit_id),
        }
        resp = await client.post(self.check_existence_url, data=data)
        assert resp.status_code == http.HTTPStatus.OK
        assert resp.json()["result"]["exists"]

        data["submitId"] = str(uuid.uuid4())
        resp = await client.post(self.check_existence_url, data=data)
        assert resp.status_code == http.HTTPStatus.OK
        assert not resp.json()["result"]["exists"]

        del data["submitId"]
        client.login(lucy)
        resp = await client.post(self.check_existence_url, data=data)
        assert resp.status_code == http.HTTPStatus.OK
        assert not resp.json()["result"]["exists"]

    @pytest.mark.parametrize(
        "user_fixture_name,expected_code",
        (
            ("tom", http.HTTPStatus.NO_CONTENT),  # owner
            ("lucy", http.HTTPStatus.FORBIDDEN),  # not in applet
            ("bob", http.HTTPStatus.FORBIDDEN),  # reviewer
        ),
    )
    async def test_review_delete(
        self,
        tom_answer_create_data,
        tom_answer_assessment_create_data,
        client,
        tom,
        applet_with_reviewable_activity,
        session,
        bob_reviewer_in_applet_with_reviewable_activity,
        user_fixture_name,
        expected_code,
        request,
        tom_answer_on_reviewable_applet,
        tom_review_answer,
    ):
        login_user = request.getfixturevalue(user_fixture_name)
        client.login(login_user)
        assessment = await AnswerItemsCRUD(session).get_assessment(tom_answer_on_reviewable_applet.id, tom.id)
        assert assessment
        response = await client.delete(
            self.assessment_delete_url.format(
                applet_id=str(applet_with_reviewable_activity.id),
                answer_id=tom_answer_on_reviewable_applet.id,
                assessment_id=assessment.id,
            )
        )
        assert response.status_code == expected_code
        assessment = await AnswerItemsCRUD(session).get_assessment(tom_answer_on_reviewable_applet.id, tom.id)
        if expected_code == 204:
            assert not assessment
        else:
            assert assessment

    async def test_summary_activities_submitted_without_answers(
        self,
        client,
        tom,
        applet_with_reviewable_activity,
    ):
        client.login(tom)
        applet_id = applet_with_reviewable_activity.id
        response = await client.get(
            self.summary_activities_url.format(
                applet_id=str(applet_id),
            )
        )
        assert response.status_code == http.HTTPStatus.OK
        payload = response.json()
        actual_last_date = payload["result"][0]["lastAnswerDate"]
        assert actual_last_date is None

    async def test_get_all_types_of_activity_identifiers(
        self, client, tom: User, applet: AppletFull, session, tom_answer_item_for_applet, tom_applet_subject
    ):
        client.login(tom)
        identifier_url = self.activity_identifiers_url.format(
            applet_id=str(applet.id), activity_id=str(applet.activities[0].id)
        )
        identifier_url = f"{identifier_url}?targetSubjectId={tom_applet_subject.id}"

        answer_items = [
            # Migrated not encrypted
            AnswerItemSchema(
                **tom_answer_item_for_applet,
                identifier="unencrypted identifier",
                migrated_data=dict(is_identifier_encrypted=False),
            ),
            # Migrated encrypted
            AnswerItemSchema(
                **tom_answer_item_for_applet,
                identifier="encrypted identifier",
                user_public_key="user_public_key",
                migrated_data=dict(is_identifier_encrypted=True),
            ),
            # Not migrated
            AnswerItemSchema(
                **tom_answer_item_for_applet,
                identifier="identifier",
                user_public_key="user_public_key",
                migrated_data=None,
            ),
        ]
        for answer_item in answer_items:
            await AnswerItemsCRUD(session).create(answer_item)

        res = await client.get(identifier_url)
        assert res.status_code == http.HTTPStatus.OK
        payload = res.json()
        assert payload["count"] == len(answer_items)
        for identifier in payload["result"]:
            assert "lastAnswerDate" in identifier
            if identifier["identifier"] in ["encrypted identifier", "identifier"]:
                assert "userPublicKey" in identifier

    async def test_summary_activities_submitted_date_with_answers(
        self,
        client,
        tom,
        applet_with_reviewable_activity,
        session,
    ):
        client.login(tom)
        applet_id = applet_with_reviewable_activity.id
        answer_service = AnswerService(session, tom.id)
        submit_dates = []
        for i in range(2):
            answer = await answer_service.create_answer(
                AppletAnswerCreate(
                    applet_id=applet_with_reviewable_activity.id,
                    version=applet_with_reviewable_activity.version,
                    submit_id=uuid.uuid4(),
                    activity_id=applet_with_reviewable_activity.activities[0].id,
                    answer=ItemAnswerCreate(
                        item_ids=[applet_with_reviewable_activity.activities[0].items[0].id],
                        start_time=datetime.datetime.utcnow(),
                        end_time=datetime.datetime.utcnow(),
                        user_public_key=str(tom.id),
                    ),
                    client=ClientMeta(app_id=f"{uuid.uuid4()}", app_version="1.1", width=984, height=623),
                )
            )
            submit_dates.append(answer.created_at)

        response = await client.get(
            self.summary_activities_url.format(
                applet_id=str(applet_id),
            )
        )
        assert response.status_code == 200
        payload = response.json()
        expected_last_date = str(max(submit_dates))
        actual_last_date = payload["result"][0]["lastAnswerDate"].replace("T", " ")
        assert actual_last_date == expected_last_date

    async def test_answer_reviewer_count_for_multiple_reviews(
        self,
        client,
        tom,
        applet_with_reviewable_activity,
        tom_answer_on_reviewable_applet,
        tom_review_answer,
        bob_review_answer,
        lucy_review_answer,
    ):
        client.login(tom)
        applet_id = applet_with_reviewable_activity.id
        activity_id = applet_with_reviewable_activity.activities[0].id
        url = self.activity_answers_url.format(applet_id=str(applet_id), activity_id=str(activity_id))
        response = await client.get(url)
        assert response.status_code == 200
        payload = response.json()
        assert payload["result"][0]["reviewCount"]["mine"] == 1
        assert payload["result"][0]["reviewCount"]["other"] == 2

    async def test_answer_reviewer_count_for_one_own_review(
        self,
        client,
        tom,
        applet_with_reviewable_activity: AppletFull,
        tom_answer_on_reviewable_applet,
        tom_review_answer,
    ):
        client.login(tom)
        applet_id = applet_with_reviewable_activity.id
        activity_id = applet_with_reviewable_activity.activities[0].id
        url = self.activity_answers_url.format(applet_id=str(applet_id), activity_id=str(activity_id))
        response = await client.get(url)
        assert response.status_code == 200
        payload = response.json()
        assert payload["result"][0]["reviewCount"]["mine"] == 1
        assert payload["result"][0]["reviewCount"]["other"] == 0

    async def test_answer_reviewer_count_for_one_other_review(
        self,
        client,
        tom,
        applet_with_reviewable_activity: AppletFull,
        tom_answer_on_reviewable_applet,
        bob_review_answer,
    ):
        client.login(tom)
        applet_id = applet_with_reviewable_activity.id
        activity_id = applet_with_reviewable_activity.activities[0].id
        url = self.activity_answers_url.format(applet_id=str(applet_id), activity_id=str(activity_id))
        response = await client.get(url)
        assert response.status_code == 200
        payload = response.json()
        assert payload["result"][0]["reviewCount"]["mine"] == 0
        assert payload["result"][0]["reviewCount"]["other"] == 1

    @pytest.mark.parametrize(
        "user_fixture,role",
        (
            ("tom", Role.OWNER),
            ("lucy", Role.MANAGER),
            ("bob", Role.REVIEWER),
        ),
    )
    async def test_owner_can_view_all_reviews_other_can_see_empty_encrypted_data(
        self,
        bob_reviewer_in_applet_with_reviewable_activity,
        lucy_manager_in_applet_with_reviewable_activity,
        tom_answer_on_reviewable_applet,
        tom_review_answer,
        bob_review_answer,
        client,
        tom,
        applet_with_reviewable_activity,
        session,
        request,
        user_fixture,
        role,
    ):
        login_user = request.getfixturevalue(user_fixture)
        client.login(login_user)
        result = await client.get(
            self.answer_reviews_url.format(
                applet_id=applet_with_reviewable_activity.id, answer_id=tom_answer_on_reviewable_applet.id
            )
        )
        assert result.status_code == 200
        payload = result.json()
        assert payload
        assert payload["count"] == 2

        results = payload["result"]
        for review in results:
            reviewer_id = uuid.UUID(review["reviewer"]["id"])
            if role == Role.REVIEWER and login_user.id != reviewer_id:
                assert review["answer"] is None
                assert review["reviewerPublicKey"] is None
            else:
                assert review["answer"] is not None
                assert review["reviewerPublicKey"] is not None

    async def test_get_summary_activities_after_upgrading_version(
        self,
        client,
        tom,
        applet_with_reviewable_activity,
        tom_answer_on_reviewable_applet,
        session,
    ):
        client.login(tom)
        answer_crud = AnswersCRUD(session)
        answer = await answer_crud.get_by_id(tom_answer_on_reviewable_applet.id)

        # Downgrade version on answer
        activity_id = answer.activity_history_id.split("_")[0]
        answer.activity_history_id = f"{activity_id}_1.0.0"
        answer.version = "1.0.0"
        await answer_crud._update_one("id", answer.id, answer)

        response = await client.get(
            self.summary_activities_url.format(
                applet_id=str(applet_with_reviewable_activity.id),
            )
        )
        assert response.status_code == 200
        assert response.json()["count"] == 1
        assert response.json()["result"][0]["hasAnswer"] is True

    async def test_review_flows_one_answer(
        self, mock_kiq_report, client, tom: User, applet_with_flow: AppletFull, tom_answer_activity_flow, session
    ):
        client.login(tom)
        url = self.review_flows_url.format(applet_id=applet_with_flow.id)

        tom_subject = await SubjectsService(session, tom.id).get_by_user_and_applet(tom.id, applet_with_flow.id)
        assert tom_subject

        response = await client.get(
            url,
            dict(
                targetSubjectId=tom_subject.id,
                createdDate=datetime.datetime.utcnow().date(),
            ),
        )
        assert response.status_code == 200
        data = response.json()
        assert "result" in data
        data = data["result"]
        assert len(data) == len(applet_with_flow.activity_flows)
        assert set(data[0].keys()) == {"id", "name", "answerDates", "lastAnswerDate"}
        for i, row in enumerate(data):
            assert row["id"] == str(applet_with_flow.activity_flows[i].id)
            assert row["name"] == applet_with_flow.activity_flows[i].name
        assert len(data[0]["answerDates"]) == 1
        assert set(data[0]["answerDates"][0].keys()) == {"submitId", "createdAt", "endDatetime"}
        assert len(data[1]["answerDates"]) == 0

    async def test_review_flows_one_answer_incomplete_submission(
        self,
        mock_kiq_report,
        client,
        tom: User,
        applet_with_flow: AppletFull,
        tom_answer_activity_flow_incomplete,
        session,
    ):
        client.login(tom)
        url = self.review_flows_url.format(applet_id=applet_with_flow.id)

        tom_subject = await SubjectsService(session, tom.id).get_by_user_and_applet(tom.id, applet_with_flow.id)
        assert tom_subject

        response = await client.get(
            url,
            dict(
                targetSubjectId=tom_subject.id,
                createdDate=datetime.datetime.utcnow().date(),
            ),
        )
        assert response.status_code == 200
        data = response.json()
        assert "result" in data
        data = data["result"]
        assert len(data) == len(applet_with_flow.activity_flows)
        assert set(data[0].keys()) == {"id", "name", "answerDates", "lastAnswerDate"}
        for i, row in enumerate(data):
            assert row["id"] == str(applet_with_flow.activity_flows[i].id)
            assert row["name"] == applet_with_flow.activity_flows[i].name
        assert len(data[0]["answerDates"]) == 0
        assert len(data[1]["answerDates"]) == 0

    async def test_review_flows_multiple_answers(
        self,
        mock_kiq_report,
        client,
        tom: User,
        applet_with_flow: AppletFull,
        tom_answer_activity_flow_multiple,
        session,
    ):
        client.login(tom)
        url = self.review_flows_url.format(applet_id=applet_with_flow.id)
        tom_subject = await SubjectsService(session, tom.id).get_by_user_and_applet(tom.id, applet_with_flow.id)
        assert tom_subject
        response = await client.get(
            url,
            dict(
                targetSubjectId=tom_subject.id,
                createdDate=datetime.datetime.utcnow().date(),
            ),
        )
        assert response.status_code == 200
        data = response.json()
        assert "result" in data
        data = data["result"]
        assert len(data) == len(applet_with_flow.activity_flows)
        assert len(data[0]["answerDates"]) == 2
        assert len(data[1]["answerDates"]) == 1

    async def test_flow_submission(self, client, tom: User, applet_with_flow: AppletFull, tom_answer_activity_flow):
        client.login(tom)
        url = self.flow_submission_url.format(
            applet_id=applet_with_flow.id,
            flow_id=applet_with_flow.activity_flows[0].id,
            submit_id=tom_answer_activity_flow.submit_id,
        )
        response = await client.get(url)
        assert response.status_code == 200
        data = response.json()
        assert "result" in data
        data = data["result"]
        assert set(data.keys()) == {"flow", "submission", "summary"}
        assert data["submission"]["isCompleted"] is True
        assert len(data["submission"]["answers"]) == len(applet_with_flow.activity_flows[0].items)
        answer_data = data["submission"]["answers"][0]
        # fmt: off
        assert set(answer_data.keys()) == {
            "activityHistoryId", "activityId", "answer", "createdAt", "endDatetime", "events", "flowHistoryId", "id",
            "identifier", "itemIds", "migratedData", "submitId", "userPublicKey", "version"
        }
        assert answer_data["submitId"] == str(tom_answer_activity_flow.submit_id)
        assert answer_data["flowHistoryId"] == str(tom_answer_activity_flow.flow_history_id)

        assert set(data["flow"].keys()) == {
            "id", "activities", "autoAssign", "createdAt", "description", "hideBadge", "idVersion", "isHidden",
            "isSingleReport",
            "name", "order", "reportIncludedActivityName", "reportIncludedItemName"
        }
        assert len(data["flow"]["activities"]) == len(applet_with_flow.activity_flows[0].items)
        assert set(data["flow"]["activities"][0].keys()) == {
            "createdAt", "isSkippable", "showAllAtOnce", "subscaleSetting", "order", "name", "isHidden",
            "scoresAndReports", "isReviewable", "idVersion", "items", "performanceTaskType", "responseIsEditable",
            "appletId", "reportIncludedItemName", "description", "id", "splashScreen", "image"
        }
        assert len(data["flow"]["activities"][0]["items"]) == len(applet_with_flow.activities[0].items)
        assert set(data["flow"]["activities"][0]["items"][0].keys()) == {
            "activityId", "allowEdit", "conditionalLogic", "config", "id", "idVersion", "isHidden", "name", "order",
            "question", "responseType", "responseValues"
        }
        assert data["flow"]["idVersion"] == tom_answer_activity_flow.flow_history_id

        assert set(data["summary"].keys()) == {"identifier", "endDatetime", "version", "createdAt"}
        assert data["summary"]["createdAt"] == tom_answer_activity_flow.created_at.strftime("%Y-%m-%dT%H:%M:%S.%f")
        assert data["summary"]["version"] == tom_answer_activity_flow.version

        assert set(data["summary"]["identifier"]) == {"lastAnswerDate", "identifier", "userPublicKey"}
        assert data["summary"]["identifier"]["identifier"] == "encrypted_identifier"
        # fmt: on

    async def test_flow_submission_incomplete(
        self, client, tom: User, applet_with_flow: AppletFull, tom_answer_activity_flow_incomplete
    ):
        client.login(tom)
        url = self.flow_submission_url.format(
            applet_id=applet_with_flow.id,
            flow_id=applet_with_flow.activity_flows[0].id,
            submit_id=tom_answer_activity_flow_incomplete.submit_id,
        )
        response = await client.get(url)
        assert response.status_code == 200
        data = response.json()
        assert "result" in data
        data = data["result"]
        assert set(data.keys()) == {"flow", "submission", "summary"}
        assert data["submission"]["isCompleted"] is False
        assert len(data["submission"]["answers"]) == len(applet_with_flow.activity_flows[0].items)

    async def test_flow_submission_no_flow(
        self, client, tom: User, applet_with_flow: AppletFull, tom_answer_activity_no_flow
    ):
        client.login(tom)
        url = self.flow_submission_url.format(
            applet_id=applet_with_flow.id,
            flow_id=applet_with_flow.activity_flows[0].id,
            submit_id=tom_answer_activity_no_flow.submit_id,
        )
        response = await client.get(url)
        assert response.status_code == 404

    async def test_summary_for_activity_flow_with_answer(
        self, client, tom: User, applet_with_flow: AppletFull, tom_answer_on_reviewable_applet, tom_answer_activity_flow
    ):
        client.login(tom)
        url = self.summary_activity_flows_url.format(applet_id=applet_with_flow.id)
        response = await client.get(url)
        assert response.status_code == 200
        payload = response.json()
        assert payload

        # TODO need proper ordering
        flow_id = str(applet_with_flow.activity_flows[0].id)
        flow_data = None
        for row in payload["result"]:
            if row["id"] == flow_id:
                flow_data = row
                break
        assert flow_data
        assert flow_data["name"] == applet_with_flow.activity_flows[0].name
        assert flow_data["hasAnswer"] is True

    async def test_summary_for_activity_flow_without_answer(
        self, client, tom: User, applet_with_flow: AppletFull, tom_answer_on_reviewable_applet
    ):
        client.login(tom)
        url = self.summary_activity_flows_url.format(applet_id=applet_with_flow.id)
        response = await client.get(url)
        assert response.status_code == 200
        payload = response.json()
        assert payload
        assert payload["count"] == len(applet_with_flow.activity_flows)

        # TODO need proper ordering
        flow_id = str(applet_with_flow.activity_flows[0].id)
        flow_data = None
        for row in payload["result"]:
            if row["id"] == flow_id:
                flow_data = row
                break
        assert flow_data
        assert flow_data["name"] == applet_with_flow.activity_flows[0].name
        assert flow_data["hasAnswer"] is False

    async def test_get_flow_submissions(
        self, mock_kiq_report, client, tom: User, applet_with_flow: AppletFull, tom_answer_activity_flow, session
    ):
        client.login(tom)
        url = self.flow_submissions_url.format(
            applet_id=applet_with_flow.id,
            flow_id=applet_with_flow.activity_flows[0].id,
        )

        tom_subject = await SubjectsService(session, tom.id).get_by_user_and_applet(tom.id, applet_with_flow.id)
        assert tom_subject
        response = await client.get(url, dict(targetSubjectId=tom_subject.id))
        assert response.status_code == 200
        data = response.json()
        assert set(data.keys()) == {"result", "count"}
        assert data["count"] == 1
        data = data["result"]
        assert set(data.keys()) == {"flows", "submissions"}

        assert len(data["submissions"]) == 1
        submission_data = data["submissions"][0]
        assert set(submission_data.keys()) == {
            "answers",
            "appletId",
            "createdAt",
            "endDatetime",
            "flowHistoryId",
            "isCompleted",
            "reviewCount",
            "submitId",
            "version",
        }
        assert submission_data["submitId"] == str(tom_answer_activity_flow.submit_id)
        answer_data = submission_data["answers"][0]
        assert answer_data["flowHistoryId"] == str(tom_answer_activity_flow.flow_history_id)

        assert len(data["flows"]) == 1
        flow_data = data["flows"][0]
        # fmt: off
        assert set(flow_data.keys()) == {
            "id", "activities", "autoAssign", "createdAt", "description", "hideBadge", "idVersion", "isHidden",
            "isSingleReport", "name", "order", "reportIncludedActivityName", "reportIncludedItemName"
        }
        assert len(flow_data["activities"]) == len(applet_with_flow.activity_flows[0].items)
        assert set(flow_data["activities"][0].keys()) == {
            "createdAt", "isSkippable", "showAllAtOnce", "subscaleSetting", "order", "name", "isHidden",
            "scoresAndReports", "isReviewable", "idVersion", "items", "performanceTaskType", "responseIsEditable",
            "appletId", "reportIncludedItemName", "description", "id", "splashScreen", "image"
        }
        assert len(flow_data["activities"][0]["items"]) == len(applet_with_flow.activities[0].items)
        assert set(flow_data["activities"][0]["items"][0].keys()) == {
            "activityId", "allowEdit", "conditionalLogic", "config", "id", "idVersion", "isHidden", "name", "order",
            "question", "responseType", "responseValues"
        }
        # fmt: on
        assert flow_data["idVersion"] == tom_answer_activity_flow.flow_history_id

    async def test_get_flow_submissions_incomplete(
        self,
        mock_kiq_report,
        client,
        tom: User,
        applet_with_flow: AppletFull,
        tom_answer_activity_flow_incomplete,
        session,
    ):
        client.login(tom)
        url = self.flow_submissions_url.format(
            applet_id=applet_with_flow.id,
            flow_id=applet_with_flow.activity_flows[0].id,
        )

        tom_subject = await SubjectsService(session, tom.id).get_by_user_and_applet(tom.id, applet_with_flow.id)
        assert tom_subject
        response = await client.get(url, dict(targetSubjectId=tom_subject.id))
        assert response.status_code == 200
        data = response.json()
        assert set(data.keys()) == {"result", "count"}
        assert data["count"] == 0
        data = data["result"]
        assert set(data.keys()) == {"flows", "submissions"}

        assert len(data["submissions"]) == 0

    @pytest.mark.parametrize(
        "query_params",
        (
            dict(identifiers="nothing"),
            dict(versions="0.0.0"),
            dict(targetSubjectId=str(uuid.uuid4())),
        ),
    )
    async def test_get_flow_submissions_filters_no_data(
        self,
        mock_kiq_report,
        client,
        tom: User,
        applet_with_flow: AppletFull,
        tom_answer_activity_flow,
        session,
        query_params,
    ):
        client.login(tom)
        url = self.flow_submissions_url.format(
            applet_id=applet_with_flow.id,
            flow_id=applet_with_flow.activity_flows[0].id,
        )
        tom_subject = await SubjectsService(session, tom.id).get_by_user_and_applet(tom.id, applet_with_flow.id)
        assert tom_subject
        query_params.setdefault("targetSubjectId", tom_subject.id)
        response = await client.get(url, query_params)
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 0
        assert not data["result"]["submissions"]
        assert not data["result"]["flows"]

    @pytest.mark.parametrize(
        "flow_index,query_params,total",
        (
            (0, dict(identifiers="encrypted_identifier"), 1),
            (0, dict(identifiers="encrypted_identifierf1a2"), 1),
            (0, dict(identifiers="encrypted_identifier,encrypted_identifierf1a2"), 2),
            (0, dict(versions="1.1.0"), 2),
            (1, dict(versions="1.1.0"), 1),
            (1, dict(identifiers="encrypted_identifierf2a1"), 1),
        ),
    )
    async def test_get_flow_submissions_filters(
        self,
        mock_kiq_report,
        client,
        tom: User,
        applet_with_flow: AppletFull,
        applet_with_flow_answer_create: list[AppletAnswerCreate],
        tom_answer_activity_flow_multiple,
        session,
        flow_index,
        query_params,
        total,
    ):
        client.login(tom)
        flow_id = applet_with_flow.activity_flows[flow_index].id
        url = self.flow_submissions_url.format(
            applet_id=applet_with_flow.id,
            flow_id=flow_id,
        )
        submissions = defaultdict(list)
        for answer in applet_with_flow_answer_create:
            if answer.flow_id != flow_id:
                continue
            if versions := query_params.get("versions"):
                if answer.version not in versions.split(","):
                    continue
            submissions[answer.submit_id].append(answer)
        # apply filters
        filtered_submissions = {}
        for submit_id, _answers in submissions.items():
            if identifiers := query_params.get("identifiers"):
                if not any(a.answer.identifier in identifiers.split(",") for a in _answers):
                    continue
            filtered_submissions[submit_id] = _answers

        tom_subject = await SubjectsService(session, tom.id).get_by_user_and_applet(tom.id, applet_with_flow.id)
        assert tom_subject
        query_params.setdefault("targetSubjectId", tom_subject.id)
        response = await client.get(url, query_params)
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == total
        assert data["count"] == len(filtered_submissions)
        assert len(data["result"]["submissions"]) == data["count"]
        for s in data["result"]["submissions"]:
            submit_id = uuid.UUID(s["submitId"])
            assert submit_id in filtered_submissions
            assert len(filtered_submissions[submit_id]) == len(s["answers"])

    @pytest.mark.usefixtures("applet_one_lucy_reviewer")
    async def test_get_summary_activity_list_admin_with_role_reviewer_and_any_other_manager_role_can_view_summary(
        self, client: TestClient, applet_one: AppletFull, lucy: User, tom: User, tom_applet_subject: Subject
    ):
        client.login(lucy)
        resp = await client.get(
            self.summary_activities_url.format(applet_id=applet_one.id),
            query={"targetSubjectId": tom_applet_subject.id},
        )
        assert resp.status_code == http.HTTPStatus.OK

    @pytest.mark.usefixtures("applet_one_lucy_reviewer")
    @pytest.mark.usefixtures("applet_one_lucy_coordinator")
    async def test_get_summary_activity_list_role_reviewer_and_coordinator(
        self, client: TestClient, applet_one: AppletFull, lucy: User, tom: User, tom_applet_subject: Subject
    ):
        client.login(lucy)
        resp = await client.get(
            self.summary_activities_url.format(applet_id=applet_one.id),
            query={"targetSubjectId": tom_applet_subject.id},
        )
        assert resp.status_code == http.HTTPStatus.OK

    @pytest.mark.parametrize(
        "role,expected",
        (
            (Role.OWNER, http.HTTPStatus.OK),
            (Role.MANAGER, http.HTTPStatus.OK),
            (Role.REVIEWER, http.HTTPStatus.OK),
            (Role.EDITOR, http.HTTPStatus.FORBIDDEN),
            (Role.COORDINATOR, http.HTTPStatus.FORBIDDEN),
            (Role.RESPONDENT, http.HTTPStatus.FORBIDDEN),
        ),
    )
    async def test_access_to_activity_list(
        self, client, tom: User, user: User, session: AsyncSession, applet, role, expected
    ):
        client.login(tom)
        applet_id = applet.id

        access_service = UserAppletAccessService(session, tom.id, applet_id)
        await access_service.add_role(user.id, role)

        url = self.summary_activities_url.format(applet_id=f"{applet_id}")
        if role == Role.REVIEWER:
            subject = await SubjectsService(session, tom.id).create(
                SubjectCreate(
                    applet_id=applet_id,
                    creator_id=tom.id,
                    first_name="first_name",
                    last_name="last_name",
                    secret_user_id=f"{uuid.uuid4()}",
                )
            )
            assert subject.id
            await access_service.set_subjects_for_review(user.id, applet_id, [subject.id])
            url = f"{url}?targetSubjectId={subject.id}"
        client.login(user)
        response = await client.get(url)
        assert response.status_code == expected

    async def test_review_flows_one_answer_without_target_subject_id(
        self, mock_kiq_report, client, tom: User, applet_with_flow: AppletFull, tom_answer_activity_flow, session
    ):
        client.login(tom)
        url = self.review_flows_url.format(applet_id=applet_with_flow.id)

        response = await client.get(
            url,
            dict(
                createdDate=datetime.datetime.utcnow().date(),
            ),
        )
        assert response.status_code == 422
        data = response.json()
        assert data["result"][0]["message"] == "field required"
        assert data["result"][0]["path"] == ["query", "targetSubjectId"]

    async def test_flow_submission_not_completed(
        self, client, tom: User, applet_with_flow: AppletFull, tom_answer_activity_flow_not_completed
    ):
        client.login(tom)
        url = self.flow_submission_url.format(
            applet_id=applet_with_flow.id,
            flow_id=applet_with_flow.activity_flows[1].id,
            submit_id=tom_answer_activity_flow_not_completed.submit_id,
        )
        response = await client.get(url)
        assert response.status_code == 200
        data = response.json()
        assert "result" in data
        data = data["result"]
        assert set(data.keys()) == {"flow", "submission", "summary"}
        assert data["submission"]["isCompleted"] is False

    async def test_get_summary_activities_no_answer_no_empty_deleted_history(
        self, client: TestClient, tom: User, applet: AppletFull
    ):
        client.login(tom)

        response = await client.get(
            self.summary_activities_url.format(
                applet_id=str(applet.id),
            )
        )

        assert response.status_code == http.HTTPStatus.OK
        assert response.json()["count"] == 1
        assert response.json()["result"][0]["name"] == applet.activities[0].name
        assert response.json()["result"][0]["id"] == str(applet.activities[0].id)
        assert not response.json()["result"][0]["isPerformanceTask"]
        assert not response.json()["result"][0]["hasAnswer"]

    async def test_activity_turned_into_assessment_not_included_in_list(
        self, client: TestClient, tom: User, applet__activity_turned_into_assessment: AppletFull
    ):
        client.login(tom)
        response = await client.get(
            self.summary_activities_url.format(
                applet_id=str(applet__activity_turned_into_assessment.id),
            )
        )

        assert response.status_code == http.HTTPStatus.OK
        assert response.json()["count"] == 1
        assert response.json()["result"][0]["id"] == str(applet__activity_turned_into_assessment.activities[1].id)

    async def test_deleted_activity_without_answers_not_included_in_list(
        self, client: TestClient, tom: User, applet__deleted_activity_without_answers: AppletFull
    ):
        client.login(tom)
        response = await client.get(
            self.summary_activities_url.format(
                applet_id=str(applet__deleted_activity_without_answers.id),
            )
        )

        assert response.status_code == http.HTTPStatus.OK
        assert response.json()["count"] == 1
        assert response.json()["result"][0]["id"] == str(applet__deleted_activity_without_answers.activities[0].id)

    async def test_deleted_flow_not_included_in_submission_list(
        self, client: TestClient, tom: User, applet__deleted_flow_without_answers: AppletFull
    ):
        client.login(tom)
        url = self.summary_activity_flows_url.format(applet_id=applet__deleted_flow_without_answers.id)
        response = await client.get(url)
        assert response.status_code == 200
        payload = response.json()
        assert applet__deleted_flow_without_answers.activity_flows[0].id
        assert payload["count"] == 1
        assert payload["result"][0]["id"] == str(applet__deleted_flow_without_answers.activity_flows[0].id)

    async def test_summary_flow_list_order_completed_submissions_only(
        self, client, tom: User, applet_with_flow: AppletFull, tom_answer_activity_flow_not_completed
    ):
        client.login(tom)
        url = self.summary_activity_flows_url.format(applet_id=applet_with_flow.id)
        response = await client.get(url)
        assert response.status_code == 200
        payload = response.json()
        assert "result" in payload
        for flow in payload["result"]:
            assert flow["hasAnswer"] is False

    async def test_summary_flow_list_order(
        self, client, tom: User, applet_with_flow: AppletFull, tom_answer_activity_flow_not_completed
    ):
        client.login(tom)
        url = self.summary_activity_flows_url.format(applet_id=applet_with_flow.id)
        response = await client.get(url)
        assert response.status_code == 200
        payload = response.json()

        assert "result" in payload
        flows_order_expected = [str(flow.id) for flow in sorted(applet_with_flow.activity_flows, key=lambda x: x.order)]
        flows_order_actual = [flow["id"] for flow in payload["result"]]
        assert flows_order_actual == flows_order_expected

    async def test_summary_activity_flow_order_with_deleted_flows(
        self, client, tom: User, applet__with_deleted_and_order: tuple[AppletFull, list[uuid.UUID]]
    ):
        client.login(tom)
        applet_id = applet__with_deleted_and_order[0].id
        flow_order_expected = applet__with_deleted_and_order[1]
        url = self.summary_activity_flows_url.format(applet_id=str(applet_id))
        response = await client.get(url)
        assert response.status_code == 200
        payload = response.json()
        assert payload
        assert len(payload["result"]) == 2
        flow_order_actual = [uuid.UUID(flow["id"]) for flow in payload["result"]]
        assert flow_order_expected == flow_order_actual

    async def test_summary_activity_order(self, client, tom: User, applet__with_ordered_activities: AppletFull):
        client.login(tom)
        applet_id = str(applet__with_ordered_activities.id)
        activities = applet__with_ordered_activities.activities
        response = await client.get(self.summary_activities_url.format(applet_id=applet_id))
        assert response.status_code == 200
        payload = response.json()
        expected_order_map = {str(a.id): a.order for a in activities}
        activity_ids = list(map(lambda x: x["id"], payload["result"]))
        assert payload
        for i in range(len(activity_ids)):
            activity_id = activity_ids[i]
            assert expected_order_map[activity_id] == i + 1

    async def test_summary_activity_order_with_deleted(
        self, client, tom: User, applet__with_deleted_activities_and_answers: AppletFull
    ):
        client.login(tom)
        applet_id = str(applet__with_deleted_activities_and_answers.id)
        activities = applet__with_deleted_activities_and_answers.activities
        response = await client.get(self.summary_activities_url.format(applet_id=applet_id))
        assert response.status_code == 200
        payload = response.json()
        assert payload
        activities_applet = sorted(activities, key=lambda x: x.order)
        activities_payload = payload["result"]
        # Validation actual activities sorted by activity.order
        for i in range(len(activities_applet)):
            activity_exp = activities[i]
            activity = activities_payload[i]
            assert str(activity_exp.id) == activity["id"]

        not_deleted_ids = [str(a.id) for a in activities_applet]
        deleted_activities = list(filter(lambda a: a["id"] not in not_deleted_ids, activities_payload))
        assert sorted(deleted_activities, key=lambda x: x["name"]) == deleted_activities

    async def test_applet_assessment_create_for_submission(
        self,
        client: TestClient,
        tom: User,
        session: AsyncSession,
        assessment_for_submission: AssessmentAnswerCreate,
        applet_with_reviewable_flow: AppletFull,
        assessment_submission_create: AssessmentAnswerCreate,
    ):
        assert assessment_submission_create.reviewed_flow_submit_id
        client.login(tom)
        applet_id = str(applet_with_reviewable_flow.id)
        flow_id = str(applet_with_reviewable_flow.activity_flows[0].id)
        submission_id = str(assessment_submission_create.reviewed_flow_submit_id)
        response = await client.post(
            self.assessment_submissions_url.format(applet_id=applet_id, flow_id=flow_id, submission_id=submission_id),
            data=assessment_submission_create,
        )
        assert response.status_code == http.HTTPStatus.CREATED
        answer = await AnswersCRUD(session).get_last_answer_in_flow(
            assessment_submission_create.reviewed_flow_submit_id
        )
        assert answer
        assessment_for_flow = await AnswerItemsCRUD(session).get_assessment(
            answer.id, tom.id, assessment_submission_create.reviewed_flow_submit_id
        )
        assert assessment_for_flow
        assert assessment_for_flow.reviewed_flow_submit_id == assessment_submission_create.reviewed_flow_submit_id

        assessment_for_act = await AnswerItemsCRUD(session).get_assessment(answer.id, tom.id)
        assert assessment_for_act
        assert assessment_for_act.reviewed_flow_submit_id is None

    async def test_applet_assessment_retrive_for_submission(
        self,
        client: TestClient,
        tom: User,
        session: AsyncSession,
        assessment_for_submission: AssessmentAnswerCreate,
        applet_with_reviewable_flow: AppletFull,
        assessment_submission_create: AssessmentAnswerCreate,
        submission_assessment_answer: AnswerItemSchema,
    ):
        assert assessment_submission_create.reviewed_flow_submit_id
        client.login(tom)
        applet_id = str(applet_with_reviewable_flow.id)
        submission_id = str(assessment_submission_create.reviewed_flow_submit_id)
        response = await client.get(
            self.assessment_submissions_retrieve_url.format(
                applet_id=applet_id,
                submission_id=submission_id,
            )
        )
        assert response.status_code == http.HTTPStatus.OK

    async def test_applet_assessment_retrive_for_submission_if_no_assessment_answer(
        self,
        client: TestClient,
        tom: User,
        session: AsyncSession,
        applet_with_reviewable_flow: AppletFull,
        assessment_submission_create: AssessmentAnswerCreate,
    ):
        assert assessment_submission_create.reviewed_flow_submit_id
        client.login(tom)
        applet_id = str(applet_with_reviewable_flow.id)
        submission_id = str(assessment_submission_create.reviewed_flow_submit_id)
        response = await client.get(
            self.assessment_submissions_retrieve_url.format(
                applet_id=applet_id,
                submission_id=submission_id,
            )
        )
        assert response.status_code == http.HTTPStatus.OK
        payload = response.json()
        assert payload["result"]["answer"] is None
        assert payload["result"]["items"] is not None

    async def test_applet_assessment_delete_for_submission(
        self,
        client: TestClient,
        tom: User,
        session: AsyncSession,
        assessment_for_submission: AssessmentAnswerCreate,
        applet_with_reviewable_flow: AppletFull,
        assessment_submission_create: AssessmentAnswerCreate,
        submission_assessment_answer: AnswerItemSchema,
    ):
        assert assessment_submission_create.reviewed_flow_submit_id
        client.login(tom)
        applet_id = str(applet_with_reviewable_flow.id)
        submission_id = str(assessment_submission_create.reviewed_flow_submit_id)
        response = await client.delete(
            self.assessment_submission_delete_url.format(
                applet_id=applet_id, submission_id=submission_id, assessment_id=submission_assessment_answer.id
            )
        )
        assert response.status_code == http.HTTPStatus.NO_CONTENT

    @pytest.mark.parametrize("user_fixture,exp_mine,exp_other", (("tom", 1, 0), ("lucy", 0, 1)))
    async def test_get_flow_submissions_review_count(
        self,
        client: TestClient,
        tom: User,
        session: AsyncSession,
        assessment_for_submission: AssessmentAnswerCreate,
        applet_with_reviewable_flow: AppletFull,
        assessment_submission_create: AssessmentAnswerCreate,
        submission_assessment_answer: AnswerItemSchema,
        lucy_manager_in_applet_with_reviewable_flow,
        request: FixtureRequest,
        user_fixture,
        exp_mine,
        exp_other,
    ):
        user: User = request.getfixturevalue(user_fixture)
        client.login(user)
        url = self.flow_submissions_url.format(
            applet_id=applet_with_reviewable_flow.id,
            flow_id=applet_with_reviewable_flow.activity_flows[0].id,
        )
        response = await client.get(url, dict(respondentId=str(tom.id)))
        assert response.status_code == 200
        data = response.json()
        assert data["result"]["submissions"][0]["reviewCount"]["mine"] == exp_mine
        assert data["result"]["submissions"][0]["reviewCount"]["other"] == exp_other

    async def test_add_submission_note(
        self,
        client: TestClient,
        tom: User,
        note_create_data: AnswerNote,
        applet_with_reviewable_flow: AppletFull,
        answers_reviewable_submission: list[AnswerSchema],
    ):
        client.login(tom)
        last_flow_answer: AnswerSchema = next(filter(lambda a: a.is_flow_completed, answers_reviewable_submission))

        response = await client.post(
            self.submission_notes_url.format(
                applet_id=applet_with_reviewable_flow.id,
                submission_id=last_flow_answer.submit_id,
                flow_id=applet_with_reviewable_flow.activity_flows[0].id,
            ),
            data=note_create_data,
        )

        assert response.status_code == http.HTTPStatus.CREATED, response.json()

        response = await client.get(
            self.submission_notes_url.format(
                applet_id=applet_with_reviewable_flow.id,
                submission_id=last_flow_answer.submit_id,
                flow_id=applet_with_reviewable_flow.activity_flows[0].id,
            )
        )

        assert response.status_code == http.HTTPStatus.OK, response.json()
        assert response.json()["count"] == 1
        note = response.json()["result"][0]
        assert note["note"] == note_create_data.note
        assert note["user"]["firstName"] == tom.first_name
        assert note["user"]["lastName"] == tom.last_name
        assert note["id"]
        assert note["createdAt"]

    async def test_edit_submission_note(
        self,
        client: TestClient,
        tom: User,
        submission_note: AnswerNoteSchema,
        applet_with_reviewable_flow: AppletFull,
        answers_reviewable_submission: list[AnswerSchema],
    ):
        client.login(tom)
        last_flow_answer: AnswerSchema = next(filter(lambda a: a.is_flow_completed, answers_reviewable_submission))
        note_new = submission_note.note + "new"
        response = await client.put(
            self.submission_note_detail_url.format(
                applet_id=applet_with_reviewable_flow.id,
                submission_id=last_flow_answer.submit_id,
                flow_id=applet_with_reviewable_flow.activity_flows[0].id,
                note_id=submission_note.id,
            ),
            dict(note=note_new),
        )
        assert response.status_code == http.HTTPStatus.OK

        response = await client.get(
            self.submission_notes_url.format(
                applet_id=applet_with_reviewable_flow.id,
                submission_id=last_flow_answer.submit_id,
                flow_id=applet_with_reviewable_flow.activity_flows[0].id,
            )
        )
        assert response.status_code == http.HTTPStatus.OK, response.json()
        assert response.json()["count"] == 1
        assert response.json()["result"][0]["note"] == note_new

    async def test_delete_submission_note(
        self,
        client: TestClient,
        tom: User,
        submission_note: AnswerNoteSchema,
        applet_with_reviewable_flow: AppletFull,
        submission_answer: AnswerSchema,
    ):
        client.login(tom)

        response = await client.delete(
            self.submission_note_detail_url.format(
                applet_id=applet_with_reviewable_flow.id,
                submission_id=submission_answer.submit_id,
                flow_id=applet_with_reviewable_flow.activity_flows[0].id,
                note_id=submission_note.id,
            )
        )

        assert response.status_code == http.HTTPStatus.NO_CONTENT

        response = await client.get(
            self.submission_notes_url.format(
                applet_id=applet_with_reviewable_flow.id,
                submission_id=submission_answer.submit_id,
                flow_id=applet_with_reviewable_flow.activity_flows[0].id,
            )
        )
        assert response.status_code == http.HTTPStatus.OK
        assert response.json()["count"] == 0

    async def test_submission_get_export_data(
        self,
        client: TestClient,
        tom: User,
        session: AsyncSession,
        assessment_for_submission: AssessmentAnswerCreate,
        applet_with_reviewable_flow: AppletFull,
        assessment_submission_create: AssessmentAnswerCreate,
        submission_assessment_answer: AnswerItemSchema,
    ):
        client.login(tom)
        response = await client.get(
            self.applet_answers_export_url.format(applet_id=str(applet_with_reviewable_flow.id)),
        )
        assert response.status_code == http.HTTPStatus.OK
        data = response.json()
        assert data["result"]["answers"]
        assert next(filter(lambda answer: answer["reviewedFlowSubmitId"], data["result"]["answers"]))

    async def test_submission_get_reviews(
        self,
        client: TestClient,
        tom: User,
        session: AsyncSession,
        assessment_for_submission: AssessmentAnswerCreate,
        applet_with_reviewable_flow: AppletFull,
        assessment_submission_create: AssessmentAnswerCreate,
        submission_assessment_answer: AnswerItemSchema,
    ):
        client.login(tom)
        result = await client.get(
            self.submission_reviews_url.format(
                applet_id=applet_with_reviewable_flow.id,
                submission_id=assessment_submission_create.reviewed_flow_submit_id,
            )
        )
        assert result.status_code == 200
        payload = result.json()
        assert payload
        assert payload["count"] == 1

    @pytest.mark.usefixtures("mock_report_server_response", "answer")
    async def test_get_latest_flow_summary(
        self,
        client: TestClient,
        tom: User,
        applet_with_flow: AppletFull,
        tom_answer_activity_flow_multiple: AnswerSchema,
        tom_applet_with_flow_subject: Subject,
    ):
        client.login(tom)
        flow_id = applet_with_flow.activity_flows[0].id
        applet_id = applet_with_flow.id
        response = await client.post(
            self.latest_flow_report_url.format(
                applet_id=str(applet_id),
                flow_id=str(flow_id),
                subject_id=str(tom_applet_with_flow_subject.id),
            ),
        )
        assert response.status_code == http.HTTPStatus.OK
        assert response.content == b"pdf body"

    @pytest.mark.parametrize(
        "query,exp_count",
        (
            ({"emptyIdentifiers": True, "identifiers": ""}, 3),
            ({"emptyIdentifiers": False, "identifiers": ""}, 2),
            ({"emptyIdentifiers": False, "identifiers": "Ident1,Ident2"}, 2),
            ({"emptyIdentifiers": False, "identifiers": "Ident1"}, 1),
        ),
    )
    async def test_applet_activity_answers_empty_identifiers_filter(
        self,
        client: TestClient,
        tom: User,
        applet: AppletFull,
        answer_ident_series: list[AnswerSchema],
        query,
        exp_count,
    ):
        client.login(tom)
        activity_id = answer_ident_series[0].activity_history_id.split("_")[0]
        response = await client.get(
            self.activity_answers_url.format(
                applet_id=str(applet.id),
                activity_id=activity_id,
            ),
            query=query,
        )
        assert response.status_code == http.HTTPStatus.OK
        res = response.json()
        assert res["count"] == exp_count

    async def test_summary_get_identifiers_deleted_from_flow(
        self, client, session, tom: User, applet__with_deleted_and_order: tuple[AppletFull, list[uuid.UUID]]
    ):
        client.login(tom)
        applet_id = applet__with_deleted_and_order[0].id
        url = self.summary_activity_flows_url.format(applet_id=str(applet_id))
        response = await client.get(url)
        assert response.status_code == 200
        payload = response.json()
        assert payload
        assert len(payload["result"]) == 2
        flow_ids = [uuid.UUID(flow["id"]) for flow in payload["result"]]
        deleted_flow_id = flow_ids[-1:][0]
        tom_subject = await SubjectsService(session, tom.id).get_by_user_and_applet(tom.id, applet_id)
        assert tom_subject
        identifier_url = self.flow_identifiers_url.format(applet_id=(applet_id), flow_id=str(deleted_flow_id))
        response = await client.get(identifier_url, dict(targetSubjectId=tom_subject.id))
        assert response.json()
        assert response.status_code == http.HTTPStatus.OK

    async def test_summary_get_versions_deleted_from_flow(
        self, client, session, tom: User, applet__with_deleted_and_order: tuple[AppletFull, list[uuid.UUID]]
    ):
        client.login(tom)
        applet_id = applet__with_deleted_and_order[0].id
        url = self.summary_activity_flows_url.format(applet_id=str(applet_id))
        response = await client.get(url)
        assert response.status_code == 200
        payload = response.json()
        assert payload
        assert len(payload["result"]) == 2
        flow_ids = [uuid.UUID(flow["id"]) for flow in payload["result"]]
        deleted_flow_id = flow_ids[-1:][0]
        tom_subject = await SubjectsService(session, tom.id).get_by_user_and_applet(tom.id, applet_id)
        assert tom_subject
        response = await client.get(
            self.flow_versions_url.format(
                applet_id=applet_id,
                flow_id=deleted_flow_id,
            )
        )
        assert response.json()
        assert response.status_code == http.HTTPStatus.OK

    async def test_summary_submissions_fow_deleted_flow_with_answers(
        self, client, session, tom: User, applet__with_deleted_and_order: tuple[AppletFull, list[uuid.UUID]]
    ):
        client.login(tom)
        applet_id = applet__with_deleted_and_order[0].id
        url = self.summary_activity_flows_url.format(applet_id=str(applet_id))
        response = await client.get(url)
        assert response.status_code == 200
        payload = response.json()
        assert payload
        assert len(payload["result"]) == 2
        flow_ids = [uuid.UUID(flow["id"]) for flow in payload["result"]]
        deleted_flow_id = flow_ids[-1:][0]
        tom_subject = await SubjectsService(session, tom.id).get_by_user_and_applet(tom.id, applet_id)
        assert tom_subject
        response = await client.get(self.flow_submissions_url.format(applet_id=str(applet_id), flow_id=deleted_flow_id))
        assert response.json()
        assert response.status_code == http.HTTPStatus.OK

    async def test_validate_multiinformant_assessment_success(
        self, client, tom: User, applet_one: AppletFull, session: AsyncSession
    ):
        client.login(tom)

        subject_service = SubjectsService(session, tom.id)

        source_subject = await subject_service.create(
            SubjectCreate(
                applet_id=applet_one.id,
                creator_id=tom.id,
                first_name="source",
                last_name="subject",
                secret_user_id=f"{uuid.uuid4()}",
            )
        )

        target_subject = await subject_service.create(
            SubjectCreate(
                applet_id=applet_one.id,
                creator_id=tom.id,
                first_name="target",
                last_name="subject",
                secret_user_id=f"{uuid.uuid4()}",
            )
        )

        url = self.multiinformat_assessment_validate_url.format(applet_id=applet_one.id)

        url = (
            f"{url}?targetSubjectId={target_subject.id}&sourceSubjectId={source_subject.id}"
            f"&activityOrFlowId={applet_one.activities[0].id}"
        )

        response = await client.get(url)

        assert response.status_code == http.HTTPStatus.OK
        assert response.json()["result"]["valid"] is True

    async def test_validate_multiinformant_assessment_success_with_flow(
        self, client, tom: User, applet_with_flow: AppletFull, session: AsyncSession
    ):
        client.login(tom)

        subject_service = SubjectsService(session, tom.id)

        source_subject = await subject_service.create(
            SubjectCreate(
                applet_id=applet_with_flow.id,
                creator_id=tom.id,
                first_name="source",
                last_name="subject",
                secret_user_id=f"{uuid.uuid4()}",
            )
        )

        target_subject = await subject_service.create(
            SubjectCreate(
                applet_id=applet_with_flow.id,
                creator_id=tom.id,
                first_name="target",
                last_name="subject",
                secret_user_id=f"{uuid.uuid4()}",
            )
        )

        url = self.multiinformat_assessment_validate_url.format(applet_id=applet_with_flow.id)

        url = (
            f"{url}?targetSubjectId={target_subject.id}&sourceSubjectId={source_subject.id}"
            f"&activityOrFlowId={applet_with_flow.activity_flows[0].id}"
        )

        response = await client.get(url)

        assert response.status_code == http.HTTPStatus.OK
        assert response.json()["result"]["valid"] is True

    async def test_validat_multiinformant_assessment_fail_not_manager(self, client, lucy: User, applet_one: AppletFull):
        client.login(lucy)

        url = self.multiinformat_assessment_validate_url.format(applet_id=applet_one.id)

        response = await client.get(url)

        assert response.status_code == http.HTTPStatus.FORBIDDEN

    async def test_validate_multiinformant_assessment_fail_no_applet(self, client, lucy: User):
        client.login(lucy)

        url = self.multiinformat_assessment_validate_url.format(applet_id=uuid.uuid4())

        response = await client.get(url)

        assert response.status_code == http.HTTPStatus.NOT_FOUND

    async def test_validate_multiinformant_assessment_success_no_params(
        self, client, tom: User, applet_one: AppletFull
    ):
        client.login(tom)

        url = self.multiinformat_assessment_validate_url.format(applet_id=applet_one.id)

        response = await client.get(url)

        assert response.status_code == http.HTTPStatus.OK
        assert response.json()["result"]["valid"] is True

    async def test_validate_multiinformant_assessment_fail_source_subject_not_found(
        self, client, tom: User, applet_one: AppletFull, applet_two: AppletFull, session: AsyncSession
    ):
        client.login(tom)

        subject_service = SubjectsService(session, tom.id)

        source_subject = await subject_service.create(
            SubjectCreate(
                applet_id=applet_two.id,
                creator_id=tom.id,
                first_name="source",
                last_name="subject",
                secret_user_id=f"{uuid.uuid4()}",
            )
        )

        target_subject = await subject_service.create(
            SubjectCreate(
                applet_id=applet_one.id,
                creator_id=tom.id,
                first_name="target",
                last_name="subject",
                secret_user_id=f"{uuid.uuid4()}",
            )
        )

        url = self.multiinformat_assessment_validate_url.format(applet_id=applet_one.id)

        url = f"{url}?targetSubjectId={target_subject.id}&sourceSubjectId={source_subject.id}"

        response = await client.get(url)

        assert response.status_code == http.HTTPStatus.OK
        assert response.json()["result"]["valid"] is False
        assert response.json()["result"]["code"] == "invalid_source_subject"

    async def test_validate_multiinformant_assessment_fail_target_subject_not_found(
        self, client, tom: User, applet_one: AppletFull, applet_two: AppletFull, session: AsyncSession
    ):
        client.login(tom)

        subject_service = SubjectsService(session, tom.id)

        source_subject = await subject_service.create(
            SubjectCreate(
                applet_id=applet_one.id,
                creator_id=tom.id,
                first_name="source",
                last_name="subject",
                secret_user_id=f"{uuid.uuid4()}",
            )
        )

        target_subject = await subject_service.create(
            SubjectCreate(
                applet_id=applet_two.id,
                creator_id=tom.id,
                first_name="target",
                last_name="subject",
                secret_user_id=f"{uuid.uuid4()}",
            )
        )

        url = self.multiinformat_assessment_validate_url.format(applet_id=applet_one.id)

        url = f"{url}?targetSubjectId={target_subject.id}&sourceSubjectId={source_subject.id}"

        response = await client.get(url)

        assert response.status_code == http.HTTPStatus.OK
        assert response.json()["result"]["valid"] is False
        assert response.json()["result"]["code"] == "invalid_target_subject"

    async def test_validate_multiinformant_assessment_fail_temporary_relation_expired(
        self,
        client,
        sam: User,
        tom: User,
        applet_one: AppletFull,
        session: AsyncSession,
        applet_one_sam_respondent,
        applet_one_sam_subject,
    ):
        client.login(sam)

        subject_service = SubjectsService(session, sam.id)

        source_subject = await subject_service.create(
            SubjectCreate(
                applet_id=applet_one.id,
                creator_id=tom.id,
                first_name="source",
                last_name="subject",
                secret_user_id=f"{uuid.uuid4()}",
            )
        )
        target_subject = await subject_service.create(
            SubjectCreate(
                applet_id=applet_one.id,
                creator_id=tom.id,
                first_name="target",
                last_name="subject",
                secret_user_id=f"{uuid.uuid4()}",
            )
        )

        # create a relation between respondent and source
        await subject_service.create_relation(
            relation="take-now",
            source_subject_id=applet_one_sam_subject.id,
            subject_id=source_subject.id,
            meta={
                "expiresAt": (datetime.datetime.now() - datetime.timedelta(days=1)).isoformat(),
            },
        )
        # create a relation between respondent and target
        await subject_service.create_relation(
            relation="take-now",
            source_subject_id=applet_one_sam_subject.id,
            subject_id=target_subject.id,
            meta={
                "expiresAt": (datetime.datetime.now() - datetime.timedelta(days=1)).isoformat(),
            },
        )

        url = self.multiinformat_assessment_validate_url.format(applet_id=applet_one.id)
        url = f"{url}?targetSubjectId={target_subject.id}&sourceSubjectId={source_subject.id}"

        response = await client.get(url)

        assert response.status_code == http.HTTPStatus.OK
        assert response.json()["result"]["valid"] is False
        assert response.json()["result"]["code"] == "no_access_to_applet"

    async def test_validate_multiinformant_assessment_success_temporary_relation_not_expired(
        self,
        client,
        sam: User,
        tom: User,
        applet_one: AppletFull,
        session: AsyncSession,
        applet_one_sam_respondent,
        applet_one_sam_subject,
    ):
        client.login(sam)

        subject_service = SubjectsService(session, sam.id)

        source_subject = await subject_service.create(
            SubjectCreate(
                applet_id=applet_one.id,
                creator_id=tom.id,
                first_name="source",
                last_name="subject",
                secret_user_id=f"{uuid.uuid4()}",
            )
        )
        target_subject = await subject_service.create(
            SubjectCreate(
                applet_id=applet_one.id,
                creator_id=tom.id,
                first_name="target",
                last_name="subject",
                secret_user_id=f"{uuid.uuid4()}",
            )
        )

        # create a relation between respondent and source
        await subject_service.create_relation(
            relation="take-now",
            source_subject_id=applet_one_sam_subject.id,
            subject_id=source_subject.id,
            meta={
                "expiresAt": (datetime.datetime.now() + datetime.timedelta(days=1)).isoformat(),
            },
        )
        # create a relation between respondent and target
        await subject_service.create_relation(
            relation="take-now",
            source_subject_id=applet_one_sam_subject.id,
            subject_id=target_subject.id,
            meta={
                "expiresAt": (datetime.datetime.now() + datetime.timedelta(days=1)).isoformat(),
            },
        )

        url = self.multiinformat_assessment_validate_url.format(applet_id=applet_one.id)
        url = f"{url}?targetSubjectId={target_subject.id}&sourceSubjectId={source_subject.id}"

        response = await client.get(url)
        assert response.status_code == http.HTTPStatus.OK
        assert response.json()["result"]["valid"] is True

    async def test_validate_multiinformant_assessment_success_permanent_non_take_now(
        self,
        client,
        sam: User,
        tom: User,
        applet_one: AppletFull,
        session: AsyncSession,
        applet_one_sam_respondent,
        applet_one_sam_subject,
    ):
        client.login(sam)

        subject_service = SubjectsService(session, sam.id)

        source_subject = await subject_service.create(
            SubjectCreate(
                applet_id=applet_one.id,
                creator_id=tom.id,
                first_name="source",
                last_name="subject",
                secret_user_id=f"{uuid.uuid4()}",
            )
        )
        target_subject = await subject_service.create(
            SubjectCreate(
                applet_id=applet_one.id,
                creator_id=tom.id,
                first_name="target",
                last_name="subject",
                secret_user_id=f"{uuid.uuid4()}",
            )
        )

        # create a relation between respondent and source
        await subject_service.create_relation(
            relation="father", source_subject_id=applet_one_sam_subject.id, subject_id=source_subject.id
        )
        # create a relation between respondent and target
        await subject_service.create_relation(
            relation="father", source_subject_id=applet_one_sam_subject.id, subject_id=target_subject.id
        )

        url = self.multiinformat_assessment_validate_url.format(applet_id=applet_one.id)
        url = f"{url}?targetSubjectId={target_subject.id}&sourceSubjectId={source_subject.id}"

        response = await client.get(url)
        assert response.status_code == http.HTTPStatus.OK
        assert response.json()["result"]["valid"] is True

    async def test_validate_multiinformant_assessment_fail_no_permissions(
        self,
        client,
        lucy: User,
        applet_one_lucy_manager: AppletFull,
    ):
        client.login(lucy)

        url = self.multiinformat_assessment_validate_url.format(applet_id=applet_one_lucy_manager.id)

        response = await client.get(url)

        assert response.status_code == http.HTTPStatus.FORBIDDEN

    async def test_validate_multiinformant_assessment_fail_no_activity(
        self, client, tom: User, applet_one: AppletFull, session: AsyncSession
    ):
        client.login(tom)

        subject_service = SubjectsService(session, tom.id)

        source_subject = await subject_service.create(
            SubjectCreate(
                applet_id=applet_one.id,
                creator_id=tom.id,
                first_name="source",
                last_name="subject",
                secret_user_id=f"{uuid.uuid4()}",
            )
        )

        target_subject = await subject_service.create(
            SubjectCreate(
                applet_id=applet_one.id,
                creator_id=tom.id,
                first_name="target",
                last_name="subject",
                secret_user_id=f"{uuid.uuid4()}",
            )
        )

        url = self.multiinformat_assessment_validate_url.format(applet_id=applet_one.id)

        url = (
            f"{url}?targetSubjectId={target_subject.id}&sourceSubjectId={source_subject.id}"
            f"&activityOrFlowId={uuid.uuid4()}"
        )

        response = await client.get(url)

        assert response.status_code == http.HTTPStatus.OK
        assert response.json()["result"]["valid"] is False
        assert response.json()["result"]["code"] == "invalid_activity_or_flow_id"

    async def test_get_applet_latest_submissions(
        self,
        client,
        tom: User,
        applet: AppletFull,
        answer_shell_account_target: dict,
    ):
        client.login(tom)

        response = await client.get(self.applet_submissions_list_url.format(applet_id=applet.id))

        assert response.status_code == 200, response.json()
        data = response.json()
        assert data["submissionsCount"] == 1
        assert data["participantsCount"] == 2
        assert len(data["submissions"]) == data["submissionsCount"]
        for s in data["submissions"]:
            assert s["targetSubjectId"] == str(answer_shell_account_target["target_subject_id"])
            assert s["targetSubjectTag"] == answer_shell_account_target["target_subject_tag"]
            assert s["targetNickname"] == answer_shell_account_target["target_nickname"]
            assert s["targetSecretUserId"] == str(answer_shell_account_target["target_secret_user_id"])
            assert s["respondentSubjectId"] == str(answer_shell_account_target["respondent_subject_id"])
            assert s["respondentSubjectTag"] == answer_shell_account_target["respondent_subject_tag"]
            assert s["respondentNickname"] == answer_shell_account_target["respondent_nickname"]
            assert s["respondentSecretUserId"] == str(answer_shell_account_target["respondent_secret_user_id"])
            assert s["sourceSubjectId"] == str(answer_shell_account_target["source_subject_id"])
            assert s["sourceSubjectTag"] == answer_shell_account_target["source_subject_tag"]
            assert s["sourceNickname"] == answer_shell_account_target["source_nickname"]
            assert s["sourceSecretUserId"] == str(answer_shell_account_target["source_secret_user_id"])
            assert s["activityName"] is not None
            assert s["activityId"] is not None

    async def test_get_applet_latest_submissions_with_deleted_subjects(
        self,
        client,
        tom: User,
        applet: AppletFull,
        answer_shell_account_target: dict,
        session: AsyncSession,
    ):
        service = SubjectsService(session, tom.id)
        await service.delete(answer_shell_account_target["target_subject_id"])
        await service.delete(answer_shell_account_target["respondent_subject_id"])
        await service.delete(answer_shell_account_target["source_subject_id"])

        client.login(tom)

        response = await client.get(self.applet_submissions_list_url.format(applet_id=applet.id))

        assert response.status_code == 200, response.json()
        data = response.json()
        assert data["submissionsCount"] == 1
        assert len(data["submissions"]) == data["submissionsCount"]
        assert data["participantsCount"] == 2
        for s in data["submissions"]:
            assert s["targetSubjectId"] == str(answer_shell_account_target["target_subject_id"])
            assert s["targetSubjectTag"] == answer_shell_account_target["target_subject_tag"]
            assert s["targetNickname"] == answer_shell_account_target["target_nickname"]
            assert s["targetSecretUserId"] == str(answer_shell_account_target["target_secret_user_id"])
            assert s["respondentSubjectId"] == str(answer_shell_account_target["respondent_subject_id"])
            assert s["respondentSubjectTag"] == answer_shell_account_target["respondent_subject_tag"]
            assert s["respondentNickname"] == answer_shell_account_target["respondent_nickname"]
            assert s["respondentSecretUserId"] == str(answer_shell_account_target["respondent_secret_user_id"])
            assert s["sourceSubjectId"] == str(answer_shell_account_target["source_subject_id"])
            assert s["sourceSubjectTag"] == answer_shell_account_target["source_subject_tag"]
            assert s["sourceNickname"] == answer_shell_account_target["source_nickname"]
            assert s["sourceSecretUserId"] == str(answer_shell_account_target["source_secret_user_id"])
            assert s["activityName"] is not None
            assert s["activityId"] is not None

    @pytest.mark.usefixtures("applet_lucy_respondent")
    async def test_get_applet_latest_submissions_pagination(
        self,
        client,
        tom: User,
        applet: AppletFull,
        answer_shell_account_target: dict,
        answer: AnswerSchema,
        lucy_answer: AnswerSchema,
    ):
        client.login(tom)

        url = self.applet_submissions_list_url.format(applet_id=applet.id)
        url = f"{url}?page=1&limit=2"

        response = await client.get(url)

        assert response.status_code == 200
        data = response.json()
        assert data["submissionsCount"] == 3
        assert data["participantsCount"] == 3
        assert len(data["submissions"]) == 2

    @pytest.mark.usefixtures("applet_lucy_respondent")
    async def test_get_applet_latest_submissions_with_flow(
        self,
        client,
        tom: User,
        applet_with_flow: AppletFull,
        tom_answer_activity_flow,
    ):
        client.login(tom)

        url = self.applet_submissions_list_url.format(applet_id=applet_with_flow.id)

        response = await client.get(url)

        assert response.status_code == 200
        data = response.json()
        assert data["submissionsCount"] == 1
        assert data["participantsCount"] == 1
        assert len(data["submissions"]) == 1

    async def test_get_applet_latest_submissions_permissions(
        self,
        client,
        user: User,
        applet: AppletFull,
    ):
        client.login(user)

        url = self.applet_submissions_list_url.format(applet_id=applet.id)

        response = await client.get(url)

        assert response.status_code == 403
