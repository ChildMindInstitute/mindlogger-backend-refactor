import uuid
from copy import deepcopy

from fastapi import Depends

from apps.alerts.crud.alert import AlertCRUD
from apps.alerts.db.schemas import AlertSchema
from apps.alerts.domain.alert import Alert, AlertPublic
from apps.alerts.errors import AlertUpdateAccessDenied, AlertViewAccessDenied
from apps.alerts.filters import AlertConfigQueryParams
from apps.authentication.deps import get_current_user
from apps.shared.domain import Response, ResponseMulti
from apps.shared.query_params import QueryParams, parse_query_params
from apps.users.domain import User
from apps.workspaces.crud.roles import UserAppletAccessCRUD
from apps.workspaces.domain.constants import Role
from infrastructure.database import atomic, session_manager


async def alert_get_all_by_applet_id(
    applet_id: uuid.UUID,
    user: User = Depends(get_current_user),
    query_params: QueryParams = Depends(
        parse_query_params(AlertConfigQueryParams)
    ),
    session=Depends(session_manager.get_session),
) -> ResponseMulti[AlertPublic]:
    # Check user permissions.
    # Only manager roles - (admin) can get alert
    async with atomic(session):
        roles = await UserAppletAccessCRUD(session).get_roles_in_roles(
            user.id,
            applet_id,
            [Role.ADMIN],
        )
        if not roles:
            raise AlertViewAccessDenied

        # Get all alert for specific applet
        instances = await AlertCRUD(session).get_by_applet_id(
            applet_id, deepcopy(query_params)
        )

        count = await AlertCRUD(session).get_by_applet_id_count(
            applet_id, deepcopy(query_params)
        )

    return ResponseMulti(
        result=[
            AlertPublic.from_orm(alert_config) for alert_config in instances
        ],
        count=count,
    )


async def alert_update_status_by_id(
    alert_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session=Depends(session_manager.get_session)
) -> Response[Alert]:
    async with atomic(session):
        alert_schema: AlertSchema = await AlertCRUD(session).get_by_id(alert_id)
        # Check user permissions.
        # Only manager roles - (admin) can update alert status
        roles = await UserAppletAccessCRUD(session).get_roles_in_roles(
            user.id,
            alert_schema.applet_id,
            [Role.ADMIN],
        )
        if not roles:
            raise AlertUpdateAccessDenied

        # Update specific alert
        instance = await AlertCRUD(session).update(alert_schema)

    alert = Alert(**instance.dict())

    return Response(result=alert)
