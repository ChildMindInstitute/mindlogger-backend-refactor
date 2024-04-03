import uuid

import pytest
from pytest import FixtureRequest
from pytest_mock import MockerFixture
from sqlalchemy.ext.asyncio import AsyncSession

from apps.applets.crud.applets import AppletsCRUD
from apps.applets.db.schemas import AppletSchema
from apps.applets.domain.applet import AppletDataRetention
from apps.applets.domain.applet_create_update import AppletReportConfiguration
from apps.applets.domain.applet_full import AppletFull
from apps.applets.domain.base import AppletBase
from apps.applets.errors import AppletNotFoundError
from apps.shared.query_params import QueryParams
from apps.users.domain import User
from apps.workspaces.domain.constants import DataRetention, Role


@pytest.fixture
def applet_link() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture
async def applet(applet_base_data: AppletBase, session: AsyncSession) -> AppletSchema:
    crud = AppletsCRUD(session)
    applet = await crud.save(AppletSchema(**applet_base_data.dict()))
    return applet


@pytest.fixture
async def applet_with_public_link(applet_link: uuid.UUID, applet: AppletSchema, session: AsyncSession) -> AppletSchema:
    crud = AppletsCRUD(session)
    updated = await crud.update_by_id(applet.id, AppletSchema(link=applet_link, require_login=False))
    assert updated.link == applet_link
    assert not updated.require_login
    return updated


@pytest.fixture
async def applet_with_link(applet_link: uuid.UUID, applet: AppletSchema, session: AsyncSession) -> AppletSchema:
    crud = AppletsCRUD(session)
    updated = await crud.update_by_id(applet.id, AppletSchema(link=applet_link, require_login=True))
    assert updated.link == applet_link
    assert updated.require_login
    return updated


@pytest.fixture
async def applet_deleted(applet: AppletSchema, session: AsyncSession):
    crud = AppletsCRUD(session)
    updated = await crud.update_by_id(applet.id, AppletSchema(is_deleted=True))
    assert updated.is_deleted
    return updated


async def test_create_applet_with_base_data(applet_base_data: AppletBase, session: AsyncSession) -> None:
    crud = AppletsCRUD(session)
    applet = await crud.save(AppletSchema(**applet_base_data.dict()))
    assert isinstance(applet.id, uuid.UUID)
    for attr, value in applet_base_data:
        assert value == getattr(applet, attr)


async def test_update_encryption_by_applet_by_id(applet: AppletSchema, session: AsyncSession) -> None:
    crud = AppletsCRUD(session)
    updated = await crud.update_by_id(applet.id, AppletSchema(encryption=None))
    assert updated.encryption is None


async def test_get_applets_by_display_name(applet: AppletSchema, session: AsyncSession) -> None:
    crud = AppletsCRUD(session)
    applets = await crud.get_by_display_name(applet.display_name, applet_ids=[applet.id], exclude_id=None)
    assert applet.id == applets[0].id


async def test_get_applets_by_display_name__id_is_excluded(applet: AppletSchema, session: AsyncSession) -> None:
    crud = AppletsCRUD(session)
    applets = await crud.get_by_display_name(applet.display_name, applet_ids=[applet.id], exclude_id=applet.id)
    assert not applets


async def test_get_applets_by_display_name__applet_not_found_by_name(
    applet_one: AppletFull, applet: AppletSchema, session: AsyncSession
) -> None:
    crud = AppletsCRUD(session)
    applets = await crud.get_by_display_name(applet_one.display_name, applet_ids=[applet.id], exclude_id=applet.id)
    assert not applets


async def test_get_applets_by_display_name__applet_id_not_in_applet_ids(
    applet_one: AppletFull, applet: AppletSchema, session: AsyncSession
) -> None:
    crud = AppletsCRUD(session)
    applets = await crud.get_by_display_name(applet.display_name, applet_ids=[applet_one.id], exclude_id=applet.id)
    assert not applets


async def test_get_applets_by_display_name__applet_deleted(applet: AppletSchema, session: AsyncSession) -> None:
    crud = AppletsCRUD(session)
    await crud.delete_by_id(applet.id)
    applets = await crud.get_by_display_name(applet.display_name, applet_ids=[applet.id], exclude_id=applet.id)
    assert not applets


@pytest.mark.parametrize(
    "applet_fixture_name, require_login, result",
    (
        ("applet_with_link", False, None),
        ("applet_with_link", True, "applet"),
        ("applet_with_public_link", False, "applet"),
        ("applet_with_public_link", True, None),
    ),
)
async def test_get_applets_by_link(
    session: AsyncSession,
    applet_fixture_name: str,
    require_login: bool,
    result: str | None,
    request: FixtureRequest,
) -> None:
    applet = request.getfixturevalue(applet_fixture_name)
    expected = applet.id if result is not None else None
    crud = AppletsCRUD(session)
    instance = await crud.get_by_link(applet.link, require_login)
    actual = instance.id if instance else None
    assert actual == expected


async def test_get_by_id(applet: AppletSchema, session: AsyncSession):
    instance = await AppletsCRUD(session).get_by_id(applet.id)
    assert instance.id == applet.id


async def test_get_by_id__applet_not_foud(applet: AppletSchema, session: AsyncSession, uuid_zero: uuid.UUID):
    with pytest.raises(AppletNotFoundError):
        await AppletsCRUD(session).get_by_id(uuid_zero)


async def test_get_by_ids(applet: AppletSchema, session: AsyncSession):
    instances = await AppletsCRUD(session).get_by_ids([applet.id])
    assert instances[0].id == applet.id


async def test_get_by_ids__applet_not_foud(applet: AppletSchema, session: AsyncSession, uuid_zero: uuid.UUID):
    instances = await AppletsCRUD(session).get_by_ids([uuid_zero])
    assert not instances


async def test_exists_by_id(applet: AppletSchema, session: AsyncSession):
    result = await AppletsCRUD(session).exist_by_id(applet.id)
    assert result


async def test_exists_by_id__applet_not_foud(applet: AppletSchema, session: AsyncSession, uuid_zero: uuid.UUID):
    result = await AppletsCRUD(session).exist_by_id(uuid_zero)
    assert not result


async def test_exists_by_id__applet_is_deleted(
    applet_deleted: AppletSchema, session: AsyncSession, uuid_zero: uuid.UUID
):
    result = await AppletsCRUD(session).exist_by_id(applet_deleted.id)
    assert not result


async def test_delete_by_id(applet: AppletSchema, session: AsyncSession):
    crud = AppletsCRUD(session)
    await crud.delete_by_id(applet.id)
    instance = await crud.get_by_id(applet.id)
    assert instance.is_deleted


async def test_create_access_link_login_not_required(
    applet: AppletSchema, session: AsyncSession, mocker: MockerFixture, uuid_zero: uuid.UUID
):
    crud = AppletsCRUD(session)
    mocker.patch("uuid.uuid4", return_value=uuid_zero)
    link = await crud.create_access_link(applet.id, False)
    assert link == uuid_zero
    instance = await crud.get_by_id(applet.id)
    assert not instance.require_login
    assert isinstance(instance.require_login, bool)


async def test_create_access_link_login_required(
    applet: AppletSchema, session: AsyncSession, mocker: MockerFixture, uuid_zero: uuid.UUID
):
    crud = AppletsCRUD(session)
    mocker.patch("uuid.uuid4", return_value=uuid_zero)
    link = await crud.create_access_link(applet.id, True)
    assert link == uuid_zero
    instance = await crud.get_by_id(applet.id)
    assert instance.require_login


async def test_create_access_link__applet_does_not_exist(
    applet: AppletSchema, session: AsyncSession, uuid_zero: uuid.UUID
):
    crud = AppletsCRUD(session)
    with pytest.raises(AppletNotFoundError):
        await crud.create_access_link(uuid_zero, True)


async def test_delete_access_link(applet_with_link: AppletSchema, session: AsyncSession):
    crud = AppletsCRUD(session)
    assert applet_with_link.link
    assert isinstance(applet_with_link.require_login, bool)
    await crud.delete_access_link(applet_with_link.id)
    updated = await crud.get_by_id(applet_with_link.id)
    assert updated.link is None
    assert updated.require_login is None


async def test_set_data_retention(applet: AppletSchema, session: AsyncSession):
    period = 90
    data_retention = AppletDataRetention(retention=DataRetention.YEARS, period=period)
    crud = AppletsCRUD(session)
    await crud.set_data_retention(applet.id, data_retention)
    updated = await crud.get_by_id(applet.id)
    assert updated.retention_period == data_retention.period
    assert updated.retention_type == data_retention.retention


async def test_publish_applet(applet: AppletSchema, session: AsyncSession):
    crud = AppletsCRUD(session)
    assert not applet.is_published
    await crud.publish_by_id(applet.id)
    updated = await crud.get_by_id(applet.id)
    assert updated.is_published


async def test_conceal_applet(applet: AppletSchema, session: AsyncSession):
    crud = AppletsCRUD(session)
    assert not applet.is_published
    await crud.publish_by_id(applet.id)
    await session.commit()
    published = await crud.get_by_id(applet.id)
    assert published.is_published
    await crud.conceal_by_id(applet.id)
    await session.commit()
    concealed = await crud.get_by_id(applet.id)
    assert not concealed.is_published


async def test_set_report_configuration(applet: AppletSchema, session: AsyncSession):
    crud = AppletsCRUD(session)
    report_configuration = AppletReportConfiguration(
        report_server_ip="localhost",
        report_email_body="email body",
        report_include_case_id=True,
        report_include_user_id=True,
        report_public_key="public key",
        report_recipients=["user@example.com"],
    )
    await crud.set_report_configuration(applet.id, report_configuration)
    updated = await crud.get_by_id(applet.id)
    for attr, val in report_configuration:
        assert val == getattr(updated, attr)


async def test_update_applet_display_name(applet: AppletSchema, session: AsyncSession):
    crud = AppletsCRUD(session)
    new_display_name = "new_display_name"
    await crud.update_display_name(applet.id, new_display_name)
    updated = await crud.get_by_id(applet.id)
    assert updated.display_name == new_display_name


@pytest.mark.parametrize("exclude,exp_count", ((True, 0), (False, 1)))
async def test_get_name_duplicates__exclude_applet(
    applet_one: AppletFull, session: AsyncSession, tom: User, exclude: bool, exp_count: int
):
    crud = AppletsCRUD(session)
    exclude_applet_id = None if not exclude else applet_one.id
    result = await crud.get_name_duplicates(tom.id, applet_one.display_name, exclude_applet_id=exclude_applet_id)
    assert len(result) == exp_count


@pytest.mark.parametrize("exclude_without_encryption,exp_count", ((True, 1), (False, 2)))
@pytest.mark.usefixtures("applet_one_no_encryption", "applet_two")
async def test_get_applets_by_roles_count(
    session: AsyncSession, tom: User, exclude_without_encryption: bool, exp_count: int
):
    crud = AppletsCRUD(session)
    count = await crud.get_applets_by_roles_count(
        tom.id, [Role.OWNER], QueryParams(search=None), exclude_without_encryption=exclude_without_encryption
    )
    assert count == exp_count
