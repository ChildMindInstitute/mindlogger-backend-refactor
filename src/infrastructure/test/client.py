import urllib.parse

from httpx import AsyncClient, Response

import registry
from infrastructure.app import create_app


class TestClient:
    def __init__(self):

        app = create_app(registry.routers, registry.middlewares)
        self.client = AsyncClient(app=app, base_url="http://test.com")

    @staticmethod
    def _prepare_url(url, query):
        return f"{url}{urllib.parse.urlencode(query)}"

    async def post(self, url, query=None, data=None, headers=None) -> Response:
        if query:
            url = self._prepare_url(url, query)
        response = await self.client.post(url, data=data, headers=headers)
        return response

    async def put(self, url, query=None, data=None, headers=None):
        if query:
            url = self._prepare_url(url, query)
        response = await self.client.put(url, data=data, headers=headers)
        return response

    async def get(self, url, query=None, headers=None):
        if query:
            url = self._prepare_url(url, query)
        response = await self.client.get(url, headers=headers)
        return response

    async def delete(self, url, query=None, headers=None):
        if query:
            url = self._prepare_url(url, query)
        response = await self.client.delete(url, headers=headers)
        return response
