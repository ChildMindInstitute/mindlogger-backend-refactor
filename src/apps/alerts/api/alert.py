import uuid
from copy import deepcopy

from fastapi import Depends

from apps.alerts.crud.alert import AlertCRUD
from apps.alerts.domain.alert import AlertPublic
from apps.alerts.domain.alert_config import AlertsConfigPublic
from apps.alerts.errors import AlertCreateAccessDenied
from apps.alerts.filters import AlertConfigQueryParams
from apps.authentication.deps import get_current_user
from apps.shared.domain import ResponseMulti
from apps.shared.query_params import QueryParams, parse_query_params
from apps.users.domain import User
from apps.workspaces.crud.roles import UserAppletAccessCRUD
from apps.workspaces.domain.constants import Role
from infrastructure.database import session_manager, atomic


async def alert_get_all_by_applet_id(
        applet_id: uuid.UUID,
        user: User = Depends(get_current_user),
        query_params: QueryParams = Depends(
            parse_query_params(AlertConfigQueryParams)
        ),
        session=Depends(session_manager.get_session),
) -> ResponseMulti[AlertPublic]:
    # Check user permissions.
    # Only manager roles - (admin, manager, editor) can get alert config
    async with atomic(session):
        roles = await UserAppletAccessCRUD(session).get_roles_in_roles(
            user.id,
            applet_id,
            [Role.ADMIN, Role.MANAGER, Role.EDITOR],
        )
        if not roles:
            raise AlertCreateAccessDenied

        # Get all alert for specific applet
        instances = await AlertCRUD(session).get_by_applet_id(
            applet_id, deepcopy(query_params)
        )

        count = await AlertCRUD(session).get_by_applet_id_count(
            applet_id, deepcopy(query_params)
        )

    return ResponseMulti(
        result=[
            AlertsConfigPublic.from_orm(alert_config)
            for alert_config in instances
        ],
        count=count,
    )
