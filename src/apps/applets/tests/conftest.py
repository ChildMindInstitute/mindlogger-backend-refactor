import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from apps.activity_flows.domain.flow_update import ActivityFlowItemUpdate, FlowUpdate
from apps.applets.crud.applets import AppletsCRUD
from apps.applets.db.schemas import AppletSchema
from apps.applets.domain.applet_create_update import AppletUpdate
from apps.applets.domain.applet_full import AppletFull
from apps.applets.domain.applet_link import CreateAccessLink
from apps.applets.service.applet import AppletService
from apps.shared.enums import Language
from apps.users.domain import User
from apps.workspaces.domain.constants import Role
from apps.workspaces.service.user_applet_access import UserAppletAccessService


@pytest.fixture
async def applet_one_no_encryption(session: AsyncSession, applet_one: AppletFull) -> AppletFull:
    crud = AppletsCRUD(session)
    instance = await crud.update_by_id(applet_one.id, AppletSchema(encryption=None))
    assert instance.encryption is None
    return applet_one


@pytest.fixture
async def applet_one_lucy_manager(session: AsyncSession, applet_one: AppletFull, tom: User, lucy: User) -> AppletFull:
    await UserAppletAccessService(session, tom.id, applet_one.id).add_role(lucy.id, Role.MANAGER)
    return applet_one


@pytest.fixture
async def applet_one_lucy_coordinator(
    session: AsyncSession, applet_one: AppletFull, tom: User, lucy: User
) -> AppletFull:
    await UserAppletAccessService(session, tom.id, applet_one.id).add_role(lucy.id, Role.COORDINATOR)
    return applet_one


@pytest.fixture
async def applet_one_with_public_link(session: AsyncSession, applet_one: AppletFull, tom: User) -> AppletFull:
    srv = AppletService(session, tom.id)
    await srv.create_access_link(applet_one.id, CreateAccessLink(require_login=False))
    applet = await srv.get_full_applet(applet_one.id)
    assert applet.link is not None
    return applet


@pytest.fixture
async def applet_one_with_link(session: AsyncSession, applet_one: AppletFull, tom: User) -> AppletFull:
    srv = AppletService(session, tom.id)
    await srv.create_access_link(applet_one.id, CreateAccessLink(require_login=True))
    applet = await srv.get_full_applet(applet_one.id)
    assert applet.link is not None
    return applet


@pytest.fixture
async def applet_one_with_flow(
    session: AsyncSession, applet_one: AppletFull, applet_minimal_data: AppletFull, tom: User
):
    data = AppletUpdate(**applet_minimal_data.dict(exclude_unset=True))
    flow = FlowUpdate(
        name="flow",
        items=[ActivityFlowItemUpdate(id=None, activity_key=data.activities[0].key)],
        description={Language.ENGLISH: "description"},
        id=None,
    )
    data.activity_flows = [flow]
    srv = AppletService(session, tom.id)
    await srv.update(applet_one.id, data)
    applet = await srv.get_full_applet(applet_one.id)
    return applet
