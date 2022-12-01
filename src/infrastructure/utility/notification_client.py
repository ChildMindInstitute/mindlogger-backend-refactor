import asyncio

from config import settings
from pyfcm import FCMNotification
from concurrent.futures.thread import ThreadPoolExecutor


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

    _initialized: bool = False
    _instance: None = None
    client: _FirebaseNotification = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, config: settings.notification, **kwargs):

        if self._initialized:
            return

        self.client = _FirebaseNotification(api_key=config.api_key)

        self._initialized = True

    async def notify(
        self,
        devices: list = None,
        message_title: str = None,
        message_body: str = None,
        time_to_live: int = None,
        data_message: dict = None,
        badge: str = None,
        extra_kwargs: dict = None,
        *args,
        **kwargs,
    ):

        try:
            if len(devices) > 1:
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
            self.notify(devices, *args, **kwargs)
