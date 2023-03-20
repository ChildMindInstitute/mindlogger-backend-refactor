import uuid
from copy import deepcopy

from fastapi import Body, Depends

from apps.activities.crud import ActivityItemsCRUD
from apps.activities.db.schemas import ActivityItemSchema
from apps.alerts.crud.alert_config import AlertConfigsCRUD
from apps.alerts.domain.alert_config import (
    AlertConfigCreate,
    AlertConfigUpdate,
    AlertsConfigCreateRequest,
    AlertsConfigPublic,
    AlertsConfigUpdateRequest,
)
from apps.alerts.errors import (
    ActivityItemNotFoundError,
    AlertConfigNotFoundError,
    AlertCreateAccessDenied,
    AnswerNotFoundError,
)
from apps.alerts.filters import AlertConfigQueryParams
from apps.authentication.deps import get_current_user
from apps.shared.domain import Response, ResponseMulti
from apps.shared.query_params import QueryParams, parse_query_params
from apps.users.domain import User
from apps.workspaces.crud.roles import UserAppletAccessCRUD
from apps.workspaces.domain.constants import Role


async def create(
    user: User = Depends(get_current_user),
    schema: AlertsConfigCreateRequest = Body(...),
) -> Response[AlertsConfigPublic]:

    # Check user permissions.
    # Only manager roles - (admin, manager, editor) can create alert config
    roles = await UserAppletAccessCRUD().get_roles_in_roles(
        user.id,
        schema.applet_id,
        [Role.ADMIN, Role.MANAGER, Role.EDITOR],
    )
    if not roles:
        raise AlertCreateAccessDenied

    # Check if answer exist in specific activity item
    activity_item: ActivityItemSchema = await ActivityItemsCRUD().get_by_id(
        schema.activity_item_id
    )
    if not activity_item:
        raise ActivityItemNotFoundError

    if schema.specific_answer not in activity_item.answers:
        raise AnswerNotFoundError

    alert_config_internal = AlertConfigCreate(**schema.dict())
    instance = await AlertConfigsCRUD().save(alert_config_internal)
    alert_config = AlertsConfigPublic(**instance.dict())

    return Response(result=alert_config)


async def update(
    alert_config_id: uuid.UUID,
    user: User = Depends(get_current_user),
    schema: AlertsConfigUpdateRequest = Body(...),
) -> Response[AlertsConfigPublic]:

    # Check user permissions.
    # Only manager roles - (admin, manager, editor) can update alert config
    roles = await UserAppletAccessCRUD().get_roles_in_roles(
        user.id,
        schema.applet_id,
        [Role.ADMIN, Role.MANAGER, Role.EDITOR],
    )
    if not roles:
        raise AlertCreateAccessDenied

    # Get alert config if exist
    instance = await AlertConfigsCRUD().get_by_id(alert_config_id)

    if not instance:
        raise AlertConfigNotFoundError

    alert_config_internal = AlertConfigUpdate(**schema.dict())
    instance = await AlertConfigsCRUD().update_by_id(
        alert_config_id, alert_config_internal
    )
    alert_config = AlertsConfigPublic(**instance.dict())

    return Response(result=alert_config)


async def get_by_id(
    alert_config_id: uuid.UUID,
    user: User = Depends(get_current_user),
) -> Response[AlertsConfigPublic]:

    # This instance is taken in order to get the applet id
    instance = await AlertConfigsCRUD().get_by_id(alert_config_id)
    if not instance:
        raise AlertConfigNotFoundError

    # Check user permissions.
    # Only manager roles - (admin, manager, editor) can get alert config
    roles = await UserAppletAccessCRUD().get_roles_in_roles(
        user.id,
        instance.applet_id,
        [Role.ADMIN, Role.MANAGER, Role.EDITOR],
    )
    if not roles:
        raise AlertCreateAccessDenied

    alert_config = AlertsConfigPublic(**instance.dict())

    return Response(result=alert_config)


async def get_all_by_applet_id(
    applet_id: uuid.UUID,
    user: User = Depends(get_current_user),
    query_params: QueryParams = Depends(
        parse_query_params(AlertConfigQueryParams)
    ),
) -> ResponseMulti[AlertsConfigPublic]:

    # Check user permissions.
    # Only manager roles - (admin, manager, editor) can get alert config
    roles = await UserAppletAccessCRUD().get_roles_in_roles(
        user.id,
        applet_id,
        [Role.ADMIN, Role.MANAGER, Role.EDITOR],
    )
    if not roles:
        raise AlertCreateAccessDenied

    # Get all alert configs for applet
    instances = await AlertConfigsCRUD().get_by_applet_id(
        applet_id, deepcopy(query_params)
    )
    if not instances:
        raise AlertConfigNotFoundError

    count = await AlertConfigsCRUD().get_by_applet_id_count(
        applet_id, deepcopy(query_params)
    )

    return ResponseMulti(
        result=[
            AlertsConfigPublic.from_orm(alert_config)
            for alert_config in instances
        ],
        count=count,
    )
