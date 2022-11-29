import asyncio

from config import settings
from pyfcm import FCMNotification
from concurrent.futures.thread import ThreadPoolExecutor


class FirebaseNotification(FCMNotification):
    """SIngleton FCM Notification client"""

    _initialized: bool = False
    _instance: None = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, config: settings.notification, **kwargs):

        if self._initialized:
            return

        super(FCMNotification, self).__init__(
            api_key=settings.notification.api_key
        )

        self._initialized = True

    def do_request(self, payload, timeout=5):
        response = self.requests_session.post(
            self.FCM_END_POINT, data=payload, timeout=timeout
        )
        if (
            "Retry-After" in response.headers
            and int(response.headers["Retry-After"]) > 0
        ):
            sleep_time = int(response.headers["Retry-After"])
            asyncio.sleep(sleep_time)
            return self.do_request(payload, timeout)
        return response

    def send_request(self, payloads=None, timeout=None):
        self.send_request_responses = []
        with ThreadPoolExecutor(max_workers=2) as executor:
            response = executor.map(self.do_request, payloads)
            executor.map(self.send_request_responses.append, response)
