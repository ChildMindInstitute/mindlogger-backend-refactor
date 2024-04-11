import uuid
from typing import cast

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from apps.applets.crud.applets import AppletsCRUD
from apps.applets.crud.applets_history import AppletHistoriesCRUD
from apps.applets.db.schemas import AppletHistorySchema, AppletSchema
from apps.applets.domain.applet_create_update import AppletReportConfiguration
from apps.applets.domain.base import AppletBase, AppletReportConfigurationBase
from apps.applets.errors import AppletVersionNotFoundError
from apps.shared.version import INITIAL_VERSION
from apps.users.domain import User


@pytest.fixture
async def applet_with_version(applet_base_data: AppletBase, session: AsyncSession) -> AppletSchema:
    crud = AppletsCRUD(session)
    applet = await crud.save(AppletSchema(**applet_base_data.dict(), version=INITIAL_VERSION))
    return applet


@pytest.fixture
async def applet_history(applet_with_version: AppletSchema, session: AsyncSession, user: User) -> AppletHistorySchema:
    crud = AppletHistoriesCRUD(session)
    history = await crud.save(
        AppletHistorySchema(
            id=applet_with_version.id,
            user_id=user.id,
            id_version=AppletHistorySchema.generate_id_version(applet_with_version.id, applet_with_version.version),
            display_name=applet_with_version.display_name,
            description=applet_with_version.description,
            about=applet_with_version.about,
            image=applet_with_version.image,
            watermark=applet_with_version.watermark,
            theme_id=applet_with_version.theme_id,
            version=applet_with_version.version,
            report_server_ip=applet_with_version.report_server_ip,
            report_public_key=applet_with_version.report_public_key,
            report_recipients=applet_with_version.report_recipients,
            report_include_user_id=applet_with_version.report_include_user_id,
            report_include_case_id=applet_with_version.report_include_case_id,
            report_email_body=applet_with_version.report_email_body,
            stream_enabled=applet_with_version.stream_enabled,
            stream_ip_address=applet_with_version.stream_ip_address,
            stream_port=applet_with_version.stream_port,
        )
    )
    return history


async def test_create_applet_version(applet_with_version: AppletSchema, session: AsyncSession, user: User):
    crud = AppletHistoriesCRUD(session)
    history = await crud.save(
        AppletHistorySchema(
            id=applet_with_version.id,
            user_id=user.id,
            id_version=AppletHistorySchema.generate_id_version(applet_with_version.id, applet_with_version.version),
            display_name=applet_with_version.display_name,
            description=applet_with_version.description,
            about=applet_with_version.about,
            image=applet_with_version.image,
            watermark=applet_with_version.watermark,
            theme_id=applet_with_version.theme_id,
            version=applet_with_version.version,
            report_server_ip=applet_with_version.report_server_ip,
            report_public_key=applet_with_version.report_public_key,
            report_recipients=applet_with_version.report_recipients,
            report_include_user_id=applet_with_version.report_include_user_id,
            report_include_case_id=applet_with_version.report_include_case_id,
            report_email_body=applet_with_version.report_email_body,
            stream_enabled=applet_with_version.stream_enabled,
            stream_ip_address=applet_with_version.stream_ip_address,
            stream_port=applet_with_version.stream_port,
        )
    )
    assert history.id_version == f"{applet_with_version.id}_{INITIAL_VERSION}"


async def test_get_by_id_version(applet_history: AppletHistorySchema, session: AsyncSession):
    crud = AppletHistoriesCRUD(session)
    history = await crud.get_by_id_version(applet_history.id_version)
    history = cast(AppletHistorySchema, history)
    assert history.id_version == applet_history.id_version


async def test_get_by_id_version__not_found_no_id(
    applet_history: AppletHistorySchema, session: AsyncSession, uuid_zero: uuid.UUID
):
    crud = AppletHistoriesCRUD(session)
    history = await crud.get_by_id_version(applet_history.generate_id_version(uuid_zero, INITIAL_VERSION))
    assert history is None


async def test_get_by_id_version__not_found_no_version(applet_history: AppletHistorySchema, session: AsyncSession):
    crud = AppletHistoriesCRUD(session)
    history = await crud.get_by_id_version(applet_history.generate_id_version(applet_history.id, "99.99.99"))
    assert history is None


async def test_retrieve_versions_by_applet_id(applet_history: AppletHistorySchema, session: AsyncSession):
    crud = AppletHistoriesCRUD(session)
    results = await crud.retrieve_versions_by_applet_id(applet_history.id)
    assert len(results) == 1


async def test_retrieve_versions_by_applet_id__not_found(
    applet_history: AppletHistorySchema, session: AsyncSession, uuid_zero: uuid.UUID
):
    crud = AppletHistoriesCRUD(session)
    results = await crud.retrieve_versions_by_applet_id(uuid_zero)
    assert not results


async def test_retrieve_by_applet_id_version(applet_history: AppletHistorySchema, session: AsyncSession):
    crud = AppletHistoriesCRUD(session)
    history = await crud.retrieve_by_applet_version(
        applet_history.generate_id_version(applet_history.id, applet_history.version)
    )
    assert history.id_version == applet_history.id_version


async def test_retrieve_by_applet_id_version__not_found(
    applet_history: AppletHistorySchema, session: AsyncSession, uuid_zero: uuid.UUID
):
    crud = AppletHistoriesCRUD(session)
    with pytest.raises(AppletVersionNotFoundError):
        await crud.retrieve_by_applet_version(applet_history.generate_id_version(uuid_zero, applet_history.version))


async def test_update_display_name(applet_history: AppletHistorySchema, session: AsyncSession):
    crud = AppletHistoriesCRUD(session)
    new_display_name = "new"
    assert applet_history.display_name != new_display_name
    await crud.update_display_name(applet_history.id_version, new_display_name)
    updated = await crud.retrieve_by_applet_version(applet_history.id_version)
    assert updated.display_name == new_display_name


async def test_get_versions_by_applet_id(applet_history: AppletHistorySchema, session: AsyncSession):
    crud = AppletHistoriesCRUD(session)
    result = await crud.get_versions_by_applet_id(applet_history.id)
    assert len(result) == 1
    assert result[0] == applet_history.version


async def test_get_versions_by_applet_id__not_found(
    applet_history: AppletHistorySchema, session: AsyncSession, uuid_zero: uuid.UUID
):
    crud = AppletHistoriesCRUD(session)
    result = await crud.get_versions_by_applet_id(uuid_zero)
    assert not result


async def test_set_report_configuration(
    applet_history: AppletHistorySchema,
    session: AsyncSession,
    applet_report_configuration_data: AppletReportConfigurationBase,
):
    crud = AppletHistoriesCRUD(session)
    schema = AppletReportConfiguration(**applet_report_configuration_data.dict())
    await crud.set_report_configuration(applet_history.id, applet_history.version, schema)
    updated = await crud.retrieve_by_applet_version(applet_history.id_version)
    for attr, val in schema:
        assert val == getattr(updated, attr)
