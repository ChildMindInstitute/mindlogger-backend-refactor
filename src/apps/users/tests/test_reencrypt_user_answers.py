import datetime
import uuid
from typing import cast
from unittest.mock import ANY

import pytest
from pytest_mock import MockerFixture
from sqlalchemy.ext.asyncio import AsyncSession

from apps.activities.domain.activity_create import ActivityItemCreate
from apps.activities.domain.response_values import SingleSelectionValues
from apps.answers.crud.answer_items import AnswerItemsCRUD
from apps.answers.crud.answers import AnswersCRUD
from apps.answers.db.schemas import AnswerSchema
from apps.answers.domain import AppletAnswerCreate, ClientMeta, ItemAnswerCreate
from apps.answers.service import AnswerEncryptor, AnswerService
from apps.applets.domain.applet_create_update import AppletCreate, AppletUpdate
from apps.applets.domain.applet_full import AppletFull
from apps.applets.service.applet import AppletService
from apps.applets.tests import constants as test_constants
from apps.job.constants import JobStatus
from apps.job.domain import Job
from apps.job.service import JobService
from apps.shared.encryption import generate_dh_aes_key, generate_dh_public_key, generate_dh_user_private_key
from apps.themes.service import ThemeService
from apps.users.domain import User, UserCreate
from apps.users.tasks import reencrypt_answers
from apps.workspaces.constants import StorageType
from apps.workspaces.domain.workspace import WorkspaceArbitraryCreate
from apps.workspaces.service.workspace import WorkspaceService

pytestmark = pytest.mark.usefixtures("mock_get_session")


@pytest.fixture
def client_meta() -> ClientMeta:
    return ClientMeta(app_id="pytest", app_version="pytest", width=0, height=0)


@pytest.fixture
def job_model(user: User) -> Job:
    return Job(
        name="reencrypt_answers",
        creator_id=user.id,
        status=JobStatus.in_progress,
        id=uuid.uuid4(),
        created_at=datetime.datetime.now(datetime.UTC),
        updated_at=datetime.datetime.now(datetime.UTC),
    )


@pytest.fixture
def applet_data(applet_minimal_data: AppletCreate):
    data = applet_minimal_data.copy(deep=True)
    data.display_name = "reencrypt answers"
    return AppletCreate(**data.dict())


@pytest.fixture
async def applet(session: AsyncSession, user: User, applet_minimal_data: AppletCreate) -> AppletFull:
    srv = AppletService(session, user.id)
    await ThemeService(session, user.id).get_or_create_default()
    applet = await srv.create(applet_minimal_data)
    return applet


@pytest.fixture
def answer_item_create(
    user: User,
    user_create: UserCreate,
    applet: AppletFull,
    single_select_item_create: ActivityItemCreate,
) -> ItemAnswerCreate:
    private_key = generate_dh_user_private_key(user.id, user_create.email, user_create.password)
    public_key = generate_dh_public_key(private_key, test_constants.TEST_PRIME, test_constants.TEST_BASE)
    aes_key = generate_dh_aes_key(private_key, test_constants.TEST_PUBLIC_KEY, test_constants.TEST_PRIME)
    encryptor = AnswerEncryptor(bytes(aes_key))
    assert applet.activities[0].items[0].response_type == single_select_item_create.response_type
    single_select_item_create.response_values = cast(
        SingleSelectionValues,
        single_select_item_create.response_values,
    )
    option = single_select_item_create.response_values.options[0]
    row_answer = str([{"value": option.value, "text": option.text}])
    encrypted_answer = encryptor.encrypt(row_answer)
    return ItemAnswerCreate(
        answer=encrypted_answer,
        events=None,
        item_ids=[applet.activities[0].items[0].id],
        identifier=None,
        scheduled_time=None,
        start_time=datetime.datetime.now(datetime.UTC),
        end_time=datetime.datetime.now(datetime.UTC) + datetime.timedelta(seconds=1),
        user_public_key=str(public_key),
    )


@pytest.fixture
async def answer(
    session: AsyncSession,
    user: User,
    applet: AppletFull,
    answer_item_create: ItemAnswerCreate,
    client_meta: ClientMeta,
) -> AnswerSchema:
    answer_create = AppletAnswerCreate(
        applet_id=applet.id,
        version=applet.version,
        submit_id=uuid.uuid4(),
        activity_id=applet.activities[0].id,
        answer=answer_item_create,
        created_at=datetime.datetime.now(datetime.UTC),
        client=client_meta,
        consent_to_share=False,
    )
    srv = AnswerService(session, user.id)
    answer = await srv.create_answer(answer_create)
    return answer


@pytest.fixture
async def answer_second(
    session: AsyncSession,
    user: User,
    applet: AppletFull,
    answer_item_create: ItemAnswerCreate,
    client_meta: ClientMeta,
) -> AnswerSchema:
    answer_create = AppletAnswerCreate(
        applet_id=applet.id,
        version=applet.version,
        submit_id=uuid.uuid4(),
        activity_id=applet.activities[0].id,
        answer=answer_item_create,
        created_at=datetime.datetime.now(datetime.UTC),
        client=client_meta,
        consent_to_share=False,
    )
    srv = AnswerService(session, user.id)
    answer = await srv.create_answer(answer_create)
    return answer


@pytest.fixture
async def answer_arbitrary(
    session: AsyncSession,
    arbitrary_session: AsyncSession,
    user: User,
    applet: AppletFull,
    answer_item_create: ItemAnswerCreate,
    client_meta: ClientMeta,
) -> AnswerSchema:
    answer_create = AppletAnswerCreate(
        applet_id=applet.id,
        version=applet.version,
        submit_id=uuid.uuid4(),
        activity_id=applet.activities[0].id,
        answer=answer_item_create,
        created_at=datetime.datetime.now(datetime.UTC),
        client=client_meta,
        consent_to_share=False,
    )
    srv = AnswerService(session, user.id, arbitrary_session=arbitrary_session)
    answer = await srv.create_answer(answer_create)
    return answer


async def test_reencrypt_answers_no_applets_job_started_with_status_in_progress(
    user: User,
    user_create: UserCreate,
    mocker: MockerFixture,
    job_model: Job,
):
    job_model.status = JobStatus.in_progress
    mocker.patch("apps.job.service.JobService.get_or_create_owned", return_value=job_model)
    # job does not exist in db, so mock update
    mocker.patch("apps.job.crud.JobCRUD.update")
    spy = mocker.spy(JobService, "change_status")
    task = await reencrypt_answers.kiq(user.id, user.email_encrypted, user_create.password, "new-pass", retries=0)
    await task.wait_result()
    # ANY - self
    spy.assert_awaited_once_with(ANY, job_model.id, JobStatus.success)


async def test_reencrypt_answers_no_applets_job_started_with_another_status(
    user: User,
    user_create: UserCreate,
    mocker: MockerFixture,
    job_model: Job,
):
    job_model.status = JobStatus.pending
    mocker.patch("apps.job.service.JobService.get_or_create_owned", return_value=job_model)
    mocker.patch("apps.job.crud.JobCRUD.update")
    spy = mocker.spy(JobService, "change_status")
    task = await reencrypt_answers.kiq(user.id, user.email_encrypted, user_create.password, "new-pass", retries=0)
    await task.wait_result()
    spy.assert_any_await(ANY, job_model.id, JobStatus.in_progress)
    spy.assert_awaited_with(ANY, job_model.id, JobStatus.success)


async def test_reencrypt_answers_no_answers(
    user: User,
    user_create: UserCreate,
    mocker: MockerFixture,
    job_model: Job,
    applet: AppletFull,
):
    job_model.status = JobStatus.in_progress
    mocker.patch("apps.job.service.JobService.get_or_create_owned", return_value=job_model)
    mocker.patch("apps.job.crud.JobCRUD.update")
    spy = mocker.spy(JobService, "change_status")
    task = await reencrypt_answers.kiq(user.id, user.email_encrypted, user_create.password, "new-pass", retries=0)
    await task.wait_result()
    spy.assert_awaited_once_with(ANY, job_model.id, JobStatus.success)


async def test_reencrypt_answers_not_valid_public_key_answer_not_reencrypted(
    session: AsyncSession,
    user: User,
    user_create: UserCreate,
    mocker: MockerFixture,
    job_model: Job,
    applet_data: AppletCreate,
    applet: AppletFull,
    answer: AnswerSchema,
):
    # TODO: capture logs
    applet_data.encryption.public_key = "not valid public key"
    answer_id = answer.id
    act_id_version = f"{applet.activities[0].id}_{applet.version}"
    answer_before = (await AnswerItemsCRUD(session).get_by_answer_and_activity(answer_id, [act_id_version]))[0].answer
    applet_update_data = AppletUpdate(**applet_data.dict(exclude_unset=True))
    await AppletService(session, user.id).update(applet.id, applet_update_data)
    job_model.status = JobStatus.in_progress
    mocker.patch("apps.job.service.JobService.get_or_create_owned", return_value=job_model)
    mocker.patch("apps.job.crud.JobCRUD.update")
    spy = mocker.spy(JobService, "change_status")
    task = await reencrypt_answers.kiq(user.id, user.email_encrypted, user_create.password, "new-pass", retries=0)
    await task.wait_result()
    spy.assert_awaited_once_with(ANY, job_model.id, JobStatus.success)
    answer_after = (await AnswerItemsCRUD(session).get_by_answer_and_activity(answer_id, [act_id_version]))[0].answer
    assert answer_before == answer_after


async def test_reencrypt_answers_success(
    session: AsyncSession,
    user: User,
    user_create: UserCreate,
    mocker: MockerFixture,
    job_model: Job,
    applet: AppletFull,
    answer: AnswerSchema,
    answer_second: AnswerSchema,
):
    answer_id = answer.id
    act_id_version = f"{applet.activities[0].id}_{applet.version}"
    answers_before = list(
        (str(i.id), i.answer)
        for i in await AnswerItemsCRUD(session).get_by_answer_and_activity(answer_id, [act_id_version])
    )
    job_model.status = JobStatus.in_progress
    mocker.patch("apps.job.service.JobService.get_or_create_owned", return_value=job_model)
    mocker.patch("apps.job.crud.JobCRUD.update")
    spy = mocker.spy(JobService, "change_status")
    task = await reencrypt_answers.kiq(user.id, user.email_encrypted, user_create.password, "new-pass", retries=0)
    await task.wait_result()
    spy.assert_awaited_once_with(ANY, job_model.id, JobStatus.success)
    answers_after = list(
        (str(i.id), i.answer)
        for i in await AnswerItemsCRUD(session).get_by_answer_and_activity(answer_id, [act_id_version])
    )
    for before, after in zip(answers_before, answers_after):
        assert before[0] == after[0]
        assert before[1] != after[1]


async def test_reencrypt_answers_exception_during_reencrypt_no_retries(
    session: AsyncSession,
    user: User,
    user_create: UserCreate,
    mocker: MockerFixture,
    job_model: Job,
    applet: AppletFull,
    answer: AnswerSchema,
):
    answer_id = answer.id
    user_id = user.id
    act_id_version = f"{applet.activities[0].id}_{applet.version}"
    answer_before = (await AnswerItemsCRUD(session).get_by_answer_and_activity(answer_id, [act_id_version]))[0].answer
    job_model.status = JobStatus.in_progress
    mocker.patch("apps.job.service.JobService.get_or_create_owned", return_value=job_model)
    mocker.patch("apps.job.crud.JobCRUD.update")
    mocker.patch("apps.answers.service.AnswerService.reencrypt_user_answers", side_effect=Exception("ERROR"))
    spy = mocker.spy(JobService, "change_status")
    task = await reencrypt_answers.kiq(user.id, user.email_encrypted, user_create.password, "new-pass", retries=0)
    await task.wait_result()
    err_msg = f"Reencryption {user_id}: cannot process applet " f"{applet.id}, skip"
    spy.assert_awaited_once_with(ANY, job_model.id, JobStatus.error, dict(errors=[err_msg, "ERROR"]))
    answer_after = (await AnswerItemsCRUD(session).get_by_answer_and_activity(answer_id, [act_id_version]))[0].answer
    assert answer_before == answer_after


async def test_reencrypt_answers_exception_during_reencrypt_with_retries(
    session: AsyncSession,
    user: User,
    user_create: UserCreate,
    mocker: MockerFixture,
    job_model: Job,
    applet: AppletFull,
    answer: AnswerSchema,
):
    answer_id = answer.id
    act_id_version = f"{applet.activities[0].id}_{applet.version}"
    answer_before = (await AnswerItemsCRUD(session).get_by_answer_and_activity(answer_id, [act_id_version]))[0].answer
    job_model.status = JobStatus.in_progress
    mocker.patch("apps.job.service.JobService.get_or_create_owned", return_value=job_model)
    mocker.patch("apps.job.crud.JobCRUD.update")
    mocker.patch("apps.answers.service.AnswerService.reencrypt_user_answers", side_effect=Exception("ERROR"))
    spy = mocker.spy(JobService, "change_status")
    task = await reencrypt_answers.kiq(user.id, user.email_encrypted, user_create.password, "new-pass", retries=1)
    await task.wait_result()
    spy.assert_any_await(ANY, job_model.id, JobStatus.retry)
    answer_after = (await AnswerItemsCRUD(session).get_by_answer_and_activity(answer_id, [act_id_version]))[0].answer
    assert answer_before == answer_after


async def test_reencrypt_answers_arbitrary(
    session: AsyncSession,
    arbitrary_session: AsyncSession,
    user: User,
    user_create: UserCreate,
    mocker: MockerFixture,
    job_model: Job,
    applet: AppletFull,
    answer_arbitrary: AnswerSchema,
    arbitrary_db_url: str,
):
    assert not await AnswersCRUD(session).count()
    assert await AnswersCRUD(arbitrary_session).count() == 1
    w = WorkspaceArbitraryCreate(
        database_uri=arbitrary_db_url,
        use_arbitrary=True,
        storage_access_key="key",
        storage_secret_key="key",
        storage_type=StorageType.AWS,
        storage_region="us-east-1",
        storage_bucket="bucket",
    )
    await WorkspaceService(session, user.id).create_workspace_from_user(user)
    await WorkspaceService(session, user.id).set_arbitrary_server(w)
    answer_id = answer_arbitrary.id
    act_id_version = f"{applet.activities[0].id}_{applet.version}"
    answer_before = (await AnswerItemsCRUD(arbitrary_session).get_by_answer_and_activity(answer_id, [act_id_version]))[
        0
    ].answer
    job_model.status = JobStatus.in_progress
    mocker.patch("apps.job.service.JobService.get_or_create_owned", return_value=job_model)
    mocker.patch("apps.job.crud.JobCRUD.update")
    spy = mocker.spy(JobService, "change_status")
    task = await reencrypt_answers.kiq(user.id, user.email_encrypted, user_create.password, "new-pass", retries=0)
    await task.wait_result()
    spy.assert_awaited_once_with(ANY, job_model.id, JobStatus.success)
    answer_after = (await AnswerItemsCRUD(arbitrary_session).get_by_answer_and_activity(answer_id, [act_id_version]))[
        0
    ].answer
    assert answer_before != answer_after
