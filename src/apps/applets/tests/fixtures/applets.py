import uuid
from typing import AsyncGenerator

import pytest
from pytest import Config
from sqlalchemy.ext.asyncio import AsyncSession

from apps.activities.domain.activity_create import ActivityCreate, ActivityItemCreate
from apps.activities.domain.response_type_config import AdditionalResponseOption, ResponseType, SingleSelectionConfig
from apps.activities.domain.response_values import SingleSelectionValues, _SingleSelectionValue
from apps.applets.crud.applets import AppletsCRUD
from apps.applets.domain.applet_create_update import AppletCreate
from apps.applets.domain.applet_full import AppletFull
from apps.applets.domain.base import AppletBase, AppletReportConfigurationBase, Encryption
from apps.applets.service.applet import AppletService
from apps.applets.tests import constants
from apps.applets.tests.utils import teardown_applet
from apps.shared.enums import Language
from apps.themes.service import ThemeService
from apps.users.domain import User
from apps.workspaces.domain.constants import Role
from apps.workspaces.service.user_applet_access import UserAppletAccessService


async def _get_or_create_applet(
    global_session: AsyncSession,
    applet_name: str,
    applet_id: uuid.UUID,
    applet_minimal_data: AppletCreate,
    user_id: uuid.UUID,
) -> AppletFull:
    crud = AppletsCRUD(global_session)
    srv = AppletService(global_session, user_id)
    applet_db = await crud._get("id", applet_id)
    if applet_db:
        applet = await srv.get_full_applet(applet_id)
    else:
        applet_data = applet_minimal_data.copy(deep=True)
        applet_data.display_name = applet_name
        applet = await srv.create(applet_data, applet_id=applet_id)
        await global_session.commit()
    return applet


@pytest.fixture(scope="session")
def encryption() -> Encryption:
    return Encryption(
        public_key=str(constants.TEST_PUBLIC_KEY),
        prime=str(constants.TEST_PRIME),
        base=str(constants.TEST_BASE),
        # Account id is not used co can be random uuid
        account_id=str(uuid.uuid4()),
    )


@pytest.fixture(scope="session")
def report_server_public_key() -> str:
    return constants.REPORT_SERVER_PUBLIC_KEY


@pytest.fixture(scope="session")
def applet_report_configuration_data(
    user: User, tom: User, report_server_public_key: str
) -> AppletReportConfigurationBase:
    return AppletReportConfigurationBase(
        report_server_ip="localhost",
        report_public_key=report_server_public_key,
        report_recipients=[tom.email_encrypted, user.email_encrypted],
    )


@pytest.fixture(scope="session")
def item_response_values() -> SingleSelectionValues:
    return SingleSelectionValues(
        palette_name=None,
        options=[
            _SingleSelectionValue(
                id=str(uuid.uuid4()),
                text="text",
                image=None,
                score=None,
                tooltip=None,
                is_hidden=False,
                color=None,
                value=0,
            )
        ],
    )


@pytest.fixture(scope="session")
def item_config() -> SingleSelectionConfig:
    return SingleSelectionConfig(
        randomize_options=False,
        timer=0,
        add_scores=False,
        add_tokens=False,
        set_alerts=False,
        add_tooltip=False,
        set_palette=False,
        remove_back_button=False,
        skippable_item=False,
        additional_response_option=AdditionalResponseOption(text_input_option=False, text_input_required=False),
    )


@pytest.fixture(scope="session")
def item_create(
    item_config: SingleSelectionConfig,
    item_response_values: SingleSelectionValues,
) -> ActivityItemCreate:
    return ActivityItemCreate(
        response_type=ResponseType.SINGLESELECT,
        response_values=item_response_values,
        config=item_config,
        question={"en": "question"},
        name="item",
    )


@pytest.fixture(scope="session")
def activity_create_session(item_create: ActivityItemCreate) -> ActivityCreate:
    return ActivityCreate(name="test", description={Language.ENGLISH: "test"}, items=[item_create], key=uuid.uuid4())


@pytest.fixture(scope="session")
def applet_base_data(encryption: Encryption) -> AppletBase:
    return AppletBase(
        display_name="Base Data",
        link=None,
        require_login=False,
        pinned_at=None,
        retention_period=None,
        retention_type=None,
        stream_enabled=True,
        stream_ip_address="127.0.0.1",
        stream_port=2323,
        encryption=encryption,
    )


@pytest.fixture(scope="session")
def applet_minimal_data(applet_base_data: AppletBase, activity_create_session: ActivityCreate) -> AppletCreate:
    # TODO: possible need to add activity_flows
    return AppletCreate(**applet_base_data.dict(), activities=[activity_create_session], activity_flows=[])


@pytest.fixture(scope="session")
async def default_theme(global_session: AsyncSession):
    theme = await ThemeService(global_session, uuid.uuid4()).get_default()
    return theme


@pytest.fixture(autouse=True, scope="session")
async def applet_one(
    global_session: AsyncSession,
    tom: User,
    applet_minimal_data: AppletCreate,
    pytestconfig: Config,
) -> AsyncGenerator[AppletFull, None]:
    applet_id = uuid.UUID("92917a56-d586-4613-b7aa-991f2c4b15b1")
    applet_name = "Applet 1"
    applet = await _get_or_create_applet(global_session, applet_name, applet_id, applet_minimal_data, tom.id)
    yield applet
    if not pytestconfig.getoption("--keepdb"):
        await teardown_applet(global_session, applet.id)


@pytest.fixture(autouse=True, scope="session")
async def applet_two(
    global_session: AsyncSession,
    tom: User,
    applet_minimal_data: AppletCreate,
    pytestconfig: Config,
) -> AsyncGenerator[AppletFull, None]:
    applet_id = uuid.UUID("92917a56-d586-4613-b7aa-991f2c4b15b2")
    applet_name = "Applet 2"
    applet = await _get_or_create_applet(global_session, applet_name, applet_id, applet_minimal_data, tom.id)
    yield applet
    if not pytestconfig.getoption("--keepdb"):
        await teardown_applet(global_session, applet.id)


@pytest.fixture(autouse=True, scope="session")
async def applet_three(
    global_session: AsyncSession,
    lucy: User,
    applet_minimal_data: AppletCreate,
    pytestconfig: Config,
) -> AsyncGenerator[AppletFull, None]:
    applet_id = uuid.UUID("92917a56-d586-4613-b7aa-991f2c4b15b3")
    applet_name = "Applet 3"
    applet = await _get_or_create_applet(global_session, applet_name, applet_id, applet_minimal_data, lucy.id)
    yield applet
    if not pytestconfig.getoption("--keepdb"):
        await teardown_applet(global_session, applet.id)


@pytest.fixture(autouse=True, scope="session")
async def applet_four(
    global_session: AsyncSession,
    bob: User,
    applet_minimal_data: AppletCreate,
    pytestconfig: Config,
) -> AsyncGenerator[AppletFull, None]:
    applet_id = uuid.UUID("92917a56-d586-4613-b7aa-991f2c4b15b4")
    applet_name = "Applet 4"
    applet = await _get_or_create_applet(global_session, applet_name, applet_id, applet_minimal_data, bob.id)
    yield applet
    if not pytestconfig.getoption("--keepdb"):
        await teardown_applet(global_session, applet.id)


@pytest.fixture
async def applet_one_lucy_editor(session: AsyncSession, applet_one: AppletFull, tom, lucy) -> AppletFull:
    await UserAppletAccessService(session, tom.id, applet_one.id).add_role(lucy.id, Role.EDITOR)
    return applet_one
