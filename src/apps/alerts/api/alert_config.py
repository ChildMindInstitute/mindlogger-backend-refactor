from fastapi import Body, Depends

from apps.activities.crud import ActivityItemsCRUD
from apps.activities.db.schemas import ActivityItemSchema
from apps.alerts.crud.alert_config import AlertConfigsCRUD
from apps.alerts.domain.alert_config import (
    AlertConfigCreate,
    AlertsConfigCreateRequest,
    AlertsConfigCreateResponse,
)
from apps.alerts.errors import (
    ActivityItemNotFoundError,
    AlertCreateAccessDenied,
    AnswerNotFoundError,
)
from apps.authentication.deps import get_current_user
from apps.shared.domain import Response
from apps.users.domain import User
from apps.workspaces.crud.roles import UserAppletAccessCRUD
from apps.workspaces.domain.constants import Role


async def alert_config_create(
    user: User = Depends(get_current_user),
    schema: AlertsConfigCreateRequest = Body(...),
) -> Response[AlertsConfigCreateResponse]:

    # Check user permissions.
    # Only manager roles - (admin, manager, editor) can create alert
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
    alert_config = AlertsConfigCreateResponse(**instance.dict())

    return Response(result=alert_config)
