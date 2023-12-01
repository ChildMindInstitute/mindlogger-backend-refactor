from fastapi import Body, Depends
from starlette.requests import Request

from apps.authentication.api.auth_utils import auth_user
from apps.authentication.domain.login import UserLoginRequest
from apps.logs.db.schemas import UserActivityLogSchema
from apps.logs.domain.constants import UserActivityEvent, UserActivityEventType
from apps.logs.services.user_activity_log import UserActivityLogService
from infrastructure.database.deps import get_session
from infrastructure.http.deps import get_mindlogger_content_source
from infrastructure.http.domain import MindloggerContentSource


async def user_activity_login_log(
    request: Request,
    user_login_schema: UserLoginRequest = Body(...),
    session=Depends(get_session),
    user=Depends(auth_user),
    mindlogger_content=Depends(get_mindlogger_content_source),
) -> None:
    if (
        mindlogger_content == MindloggerContentSource.undefined.name
        and user_login_schema.device_id
    ):
        mindlogger_content = MindloggerContentSource.mobile.name

    schema = UserActivityLogSchema(
        user_id=user.id,
        device_id=user_login_schema.device_id,
        event_type=UserActivityEventType.LOGIN,
        event=UserActivityEvent.LOGIN,
        user_agent=request.headers.get("user-agent"),
        mindlogger_content=mindlogger_content,
    )
    await UserActivityLogService(session).create_log(schema)
