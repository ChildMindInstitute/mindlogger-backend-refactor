import asyncio
from concurrent.futures.thread import ThreadPoolExecutor

from pyfcm import FCMNotification

from config import settings


class RetryException(Exception):
    def __init__(self, timeout):
        self.timeout = timeout


class _FirebaseNotification(FCMNotification):
    def do_request(self, payload, timeout=5):
        response = self.requests_session.post(
            self.FCM_END_POINT, data=payload, timeout=timeout
        )
        if (
            "Retry-After" in response.headers
            and int(response.headers["Retry-After"]) > 0
        ):
            raise RetryException(timeout=timeout)
        return response

    def send_request(self, payloads=None, timeout=None):

        self.send_request_responses = []
        with ThreadPoolExecutor(max_workers=2) as executor:
            response = executor.map(self.do_request, payloads)
            executor.map(self.send_request_responses.append, response)


class Notification:
    """SIngleton FCM Notification client"""

    _initialized = False
    _instance = None
    client: _FirebaseNotification | None = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, **kwargs):

        if self._initialized:
            return

        self.client = _FirebaseNotification(
            api_key=settings.notification.api_key
        )

        self._initialized = True

    async def notify(
        self,
        devices: list | None = None,
        message_title: str | None = None,
        message_body: str | None = None,
        time_to_live: int | None = None,
        data_message: dict | None = None,
        badge: str | None = None,
        extra_kwargs: dict | None = None,
        *args,
        **kwargs,
    ):

        try:
            if devices and len(devices) > 1:
                if self.client:
                    self.client.notify_multiple_devices(
                        registration_ids=devices,
                        message_title=message_title,
                        message_body=message_body,
                        time_to_live=time_to_live,
                        data_message=data_message,
                        badge=badge,
                        extra_kwargs=extra_kwargs,
                        *args,
                        **kwargs,
                    )
            else:
                if self.client:
                    assert devices
                    self.client.notify_single_device(
                        registration_id=devices[0],
                        message_title=message_title,
                        message_body=message_body,
                        time_to_live=time_to_live,
                        data_message=data_message,
                        badge=badge,
                        extra_kwargs=extra_kwargs,
                        *args,
                        **kwargs,
                    )
        except RetryException as ex:
            await asyncio.sleep(ex.timeout)
            await self.notify(devices, *args, **kwargs)
