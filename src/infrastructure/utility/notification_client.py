import asyncio
import enum
import json
import uuid
from collections import defaultdict

import firebase_admin
from firebase_admin import credentials, messaging

from apps.shared.domain import InternalModel
from config import settings


class FirebaseNotificationType(str, enum.Enum):
    RESPONSE = "response-data-alert"
    APPLET_UPDATE = "applet-update-alert"
    APPLET_DELETE = "applet-delete-alert"
    SCHEDULE_UPDATED = "schedule-updated"


class FirebaseData(InternalModel):
    type: FirebaseNotificationType
    applet_id: uuid.UUID
    is_local: str = "false"


class FirebaseMessage(InternalModel):
    title: str
    body: str
    data: FirebaseData


class FCMNotificationTest:
    notifications: dict[str, list] = defaultdict(list)

    async def notify(
        self,
        devices: list,
        message: FirebaseMessage,
        time_to_live: int | None = None,
        badge: str | None = None,
        extra_kwargs: dict | None = None,
        *args,
        **kwargs,
    ):
        if not devices:
            return
        for device in devices:
            self.notifications[device].append(
                json.dumps(message.dict(by_alias=True), default=str)
            )


class FCMNotification:
    """Singleton FCM Notification client"""

    def __new__(cls, *args, **kwargs):
        if settings.env == "testing":
            return FCMNotificationTest()
        return super().__new__(cls)

    def _init_app(self):
        certificate = settings.fcm.certificate
        for key, value in certificate.items():
            if not value:
                return

        return firebase_admin.initialize_app(
            credentials.Certificate(settings.fcm.certificate)
        )

    async def notify(
        self,
        devices: list,
        message: FirebaseMessage,
        time_to_live: int | None = None,
        badge: str | None = None,
        extra_kwargs: dict | None = None,
        *args,
        **kwargs,
    ):
        await asyncio.to_thread(
            self.notify_sync,
            devices,
            message,
            time_to_live,
            badge,
            extra_kwargs,
            *args,
            **kwargs,
        )

    def notify_sync(
        self,
        devices: list,
        message: FirebaseMessage,
        time_to_live: int | None = None,
        badge: str | None = None,
        extra_kwargs: dict | None = None,
        *args,
        **kwargs,
    ):
        app = self._init_app()
        if not app:
            return

        devices = list(set(devices))
        if len(devices) == 0:
            return
        elif devices and len(devices) > 1:
            messaging.send_each_for_multicast(
                messaging.MulticastMessage(
                    devices,
                    android=messaging.AndroidConfig(
                        ttl=settings.fcm.ttl, priority="high"
                    ),
                    data=dict(
                        message=json.dumps(
                            message.dict(by_alias=True), default=str
                        )
                    ),
                    apns=messaging.APNSConfig(
                        payload=messaging.APNSPayload(
                            aps=messaging.Aps(content_available=True)
                        )
                    ),
                ),
                app=app,
            )
        else:
            messaging.send(
                messaging.Message(
                    android=messaging.AndroidConfig(
                        ttl=settings.fcm.ttl, priority="high"
                    ),
                    data=dict(
                        message=json.dumps(
                            message.dict(by_alias=True), default=str
                        )
                    ),
                    token=devices[0],
                    apns=messaging.APNSConfig(
                        payload=messaging.APNSPayload(
                            aps=messaging.Aps(content_available=True)
                        )
                    ),
                ),
                app=app,
            )
