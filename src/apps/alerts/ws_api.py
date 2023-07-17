import asyncio
import json
import traceback

from fastapi import Depends
from starlette.websockets import WebSocket
from websockets.exceptions import ConnectionClosed

from apps.alerts.domain import AlertMessage
from apps.applets.crud import AppletHistoriesCRUD
from apps.authentication.deps import get_current_user_for_ws
from apps.shared.exception import ValidationError
from apps.users import User
from apps.workspaces.crud.user_applet_access import UserAppletAccessCRUD
from apps.workspaces.domain.constants import Role
from infrastructure.database.deps import pass_session
from infrastructure.utility import RedisCache


async def ws_get_alert_messages(
    websocket: WebSocket,
    user: User = Depends(get_current_user_for_ws),
):
    await websocket.accept(websocket.headers.get("sec-websocket-protocol"))
    task = asyncio.create_task(_handle_websocket(websocket, user.id))
    try:
        while True:
            await websocket.receive_text()
    finally:
        await websocket.close()
        task.cancel()


@pass_session
async def _handle_websocket(websocket, user_id, session):
    channel = f"channel_{user_id}"

    cache = RedisCache()
    async for raw_message in cache.messages(channel):
        data = raw_message["data"]
        try:
            alert_message = AlertMessage(**json.loads(data))
        except (ValidationError, TypeError):
            continue
        try:
            respondent_access = await UserAppletAccessCRUD(
                session
            ).get_applet_role_by_user_id(
                alert_message.applet_id,
                alert_message.respondent_id,
                Role.RESPONDENT,
            )
            applet_history = await AppletHistoriesCRUD(
                session
            ).retrieve_by_applet_version(
                f"{alert_message.applet_id}_{alert_message.version}"
            )
        except Exception as e:
            traceback.print_tb(e.__traceback__)
            continue
        try:
            await websocket.send_json(
                dict(
                    id=alert_message.id,
                    applet_id=str(alert_message.applet_id),
                    applet_name=applet_history.display_name,
                    version=alert_message.version,
                    secret_id=respondent_access.meta.get(
                        "secretUserId", "Anonymous"
                    ),
                    activity_id=alert_message.activity_id,
                    activity_item_id=alert_message.activity_item_id,
                    message=alert_message.message,
                    created_at=alert_message.created_at.isoformat(),
                    answer_id=str(alert_message.answer_id),
                )
            )
        except ConnectionClosed:
            break
