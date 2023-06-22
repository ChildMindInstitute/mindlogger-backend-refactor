import uuid
from copy import deepcopy

from fastapi import Body, Depends

from apps.activities.crud import ActivityItemHistoriesCRUD
from apps.activities.db.schemas import ActivityItemHistorySchema
from apps.alerts.crud.alert_config import AlertConfigsCRUD
from apps.alerts.domain.alert_config import (
    AlertConfigCreate,
    AlertConfigUpdate,
    AlertsConfigCreateRequest,
    AlertsConfigPublic,
    AlertsConfigUpdateRequest,
)
from apps.alerts.errors import (
    ActivityItemHistoryNotFoundError,
    AlertConfigNotFoundError,
    AlertCreateAccessDenied,
    AnswerNotFoundError,
)
from apps.alerts.filters import AlertConfigQueryParams
from apps.authentication.deps import get_current_user
from apps.shared.domain import Response, ResponseMulti
from apps.shared.query_params import QueryParams, parse_query_params
from apps.users.domain import User
from apps.workspaces.crud.user_applet_access import UserAppletAccessCRUD
from apps.workspaces.domain.constants import Role
from infrastructure.database import atomic
from infrastructure.database.deps import get_session


async def alert_config_create(
    user: User = Depends(get_current_user),
    schema: AlertsConfigCreateRequest = Body(...),
    session=Depends(get_session),
) -> Response[AlertsConfigPublic] | None:
    async with atomic(session):
        # Check user permissions.
        # Only manager roles - (admin, manager, editor) can create alert config
        roles = await UserAppletAccessCRUD(session).get_roles_in_roles(
            user.id,
            schema.applet_id,
            [Role.OWNER, Role.MANAGER, Role.EDITOR],
        )
        if not roles:
            raise AlertCreateAccessDenied

        # Check if answer exist in specific activity item history
        activity: ActivityItemHistorySchema = await ActivityItemHistoriesCRUD(
            session
        ).retrieve_by_id_version(schema.activity_item_histories_id_version)
        if not activity:
            raise ActivityItemHistoryNotFoundError

        if activity.response_type == "singleSelect":
            response_values = activity.response_values["options"]
            values = list()
            for value in response_values:
                values.append(value["text"])
            if schema.specific_answer in values:
                alert_config_internal = AlertConfigCreate(**schema.dict())
                instance = await AlertConfigsCRUD(session).save(
                    alert_config_internal
                )
                alert_config = AlertsConfigPublic(**instance.dict())
                return Response(result=alert_config)
            else:
                raise AnswerNotFoundError
        else:
            # logic for others response_type is not implemented yet
            return None


async def alert_config_update(
    alert_config_id: uuid.UUID,
    user: User = Depends(get_current_user),
    schema: AlertsConfigUpdateRequest = Body(...),
    session=Depends(get_session),
) -> Response[AlertsConfigPublic]:
    async with atomic(session):
        # Check user permissions.
        # Only manager roles - (admin, manager, editor) can update alert config
        roles = await UserAppletAccessCRUD(session).get_roles_in_roles(
            user.id,
            schema.applet_id,
            [Role.OWNER, Role.MANAGER, Role.EDITOR],
        )
        if not roles:
            raise AlertCreateAccessDenied

        # Get alert config if exist
        instance = await AlertConfigsCRUD(session).get_by_id(alert_config_id)

        if not instance:
            raise AlertConfigNotFoundError

        alert_config_internal = AlertConfigUpdate(**schema.dict())
        instance = await AlertConfigsCRUD(session).update_by_id(
            alert_config_id, alert_config_internal
        )
        alert_config = AlertsConfigPublic(**instance.dict())

    return Response(result=alert_config)


async def alert_config_get_by_id(
    alert_config_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session=Depends(get_session),
) -> Response[AlertsConfigPublic]:
    async with atomic(session):
        # This instance is taken in order to get the applet id
        instance = await AlertConfigsCRUD(session).get_by_id(alert_config_id)
        if not instance:
            raise AlertConfigNotFoundError

        # Check user permissions.
        # Only manager roles - (admin, manager, editor) can get alert config
        roles = await UserAppletAccessCRUD(session).get_roles_in_roles(
            user.id,
            instance.applet_id,
            [Role.OWNER, Role.MANAGER, Role.EDITOR],
        )
        if not roles:
            raise AlertCreateAccessDenied

        alert_config = AlertsConfigPublic(**instance.dict())

    return Response(result=alert_config)


async def alert_config_get_all_by_applet_id(
    applet_id: uuid.UUID,
    user: User = Depends(get_current_user),
    query_params: QueryParams = Depends(
        parse_query_params(AlertConfigQueryParams)
    ),
    session=Depends(get_session),
) -> ResponseMulti[AlertsConfigPublic]:
    async with atomic(session):
        # Check user permissions.
        # Only manager roles - (admin, manager, editor) can get alert config
        roles = await UserAppletAccessCRUD(session).get_roles_in_roles(
            user.id,
            applet_id,
            [Role.OWNER, Role.MANAGER, Role.EDITOR],
        )
        if not roles:
            raise AlertCreateAccessDenied

        # Get all alert configs for specific applet
        instances = await AlertConfigsCRUD(session).get_by_applet_id(
            applet_id, deepcopy(query_params)
        )
        if not instances:
            raise AlertConfigNotFoundError

        count = await AlertConfigsCRUD(session).get_by_applet_id_count(
            applet_id, deepcopy(query_params)
        )

    return ResponseMulti(
        result=[
            AlertsConfigPublic.from_orm(alert_config)
            for alert_config in instances
        ],
        count=count,
    )
