from broker import broker
from infrastructure.utility.notification_client import FCMNotification, FirebaseMessage


@broker.task()
async def send_push_notification(device_ids: list[str], message: dict) -> None:
    """Send a push notification to the given devices from the worker."""
    await FCMNotification().notify(device_ids, FirebaseMessage.model_validate(message))
