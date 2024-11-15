import asyncio
import enum
import json
import uuid
from collections import defaultdict

import firebase_admin
from firebase_admin import credentials, messaging

from apps.shared.domain import InternalModel
from config import settings


class FirebaseNotificationType(enum.StrEnum):
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
            self.notifications[device].append(json.dumps(message.dict(by_alias=True), default=str))


class FCMNotification:
    """Singleton FCM Notification client"""

    _initialized = False
    _app = None

    def __new__(cls, *args, **kwargs):
        if settings.env == "testing":
            return FCMNotificationTest()
        if not cls._app:
            cls._app = super().__new__(cls)
        return cls._app

    def __init__(self):
        if self._initialized:
            return
        certificate = settings.fcm.certificate
        for key, value in certificate.items():
            if not value:
                return

        self._app = firebase_admin.initialize_app(credentials.Certificate(settings.fcm.certificate))

        self._initialized = True

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
        if not self._initialized:
            return
        devices = list(set(devices))
        if len(devices) == 0:
            return
        elif devices and len(devices) > 1:
            await asyncio.to_thread(
                messaging.send_each_for_multicast,
                messaging.MulticastMessage(
                    devices,
                    android=messaging.AndroidConfig(ttl=settings.fcm.ttl, priority="high"),
                    data=dict(message=json.dumps(message.dict(by_alias=True), default=str)),
                    apns=messaging.APNSConfig(
                        headers={"apns-priority": "5"},
                        payload=messaging.APNSPayload(aps=messaging.Aps(content_available=True)),
                    ),
                ),
                app=self._app,
            )
        else:
            await asyncio.to_thread(
                messaging.send,
                messaging.Message(
                    android=messaging.AndroidConfig(ttl=settings.fcm.ttl, priority="high"),
                    data=dict(message=json.dumps(message.dict(by_alias=True), default=str)),
                    token=devices[0],
                    apns=messaging.APNSConfig(
                        headers={"apns-priority": "5"},
                        payload=messaging.APNSPayload(aps=messaging.Aps(content_available=True)),
                    ),
                ),
                app=self._app,
            )
