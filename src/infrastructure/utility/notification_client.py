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

    async def notify(self, devices: list = None, *args, **kwargs):
        try:
            if len(devices) > 1:
                self.client.notify_multiple_devices(
                    registration_ids=devices, *args, **kwargs
                )
            else:
                self.client.notify_single_device(
                    registration_id=devices[0], *args, **kwargs
                )
        except RetryException as ex:
            await asyncio.sleep(ex.timeout)
            self.notify(devices, *args, **kwargs)
