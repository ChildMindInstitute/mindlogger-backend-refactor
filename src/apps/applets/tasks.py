import uuid

from apps.applets.service import AppletService
from broker import broker
from infrastructure.database import session_manager
from infrastructure.utility import FirebaseNotificationType


@broker.task()
async def notify_respondents(
    applet_id: uuid.UUID,
    user_id: uuid.UUID,
    title: str,
    body: str,
    type_: FirebaseNotificationType,
    *,
    device_ids: list[uuid.UUID] | None = None,
    respondent_ids: list[uuid.UUID] | None = None,
):
    session_maker = session_manager.get_session()
    try:
        async with session_maker() as session:
            service = AppletService(session, user_id)
            await service.send_notification_to_applet_respondents(
                applet_id,
                title,
                body,
                type_,
                device_ids=device_ids,
                respondent_ids=respondent_ids,
            )
    finally:
        await session_maker.remove()
