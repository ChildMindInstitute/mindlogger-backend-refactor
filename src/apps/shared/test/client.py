import json
import urllib.parse

from httpx import AsyncClient, Response

from apps.authentication.domain.login import UserLoginRequest
from infrastructure.app import create_app


class TestClient:
    def __init__(self):
        app = create_app()
        self.client = AsyncClient(app=app, base_url="http://test.com")
        self.headers = {}

    @staticmethod
    def _prepare_url(url, query):
        return f"{url}{urllib.parse.urlencode(query)}"

    def _get_updated_headers(self, headers: dict | None = None) -> dict:
        headers_ = dict(self.headers)
        if headers:
            headers_.update(headers)
        return headers_

    @staticmethod
    def _get_body(data: dict | None = None):
        if data:
            return json.dumps(data)
        return {}

    async def post(
        self,
        url: str,
        data: dict | None = None,
        query: dict | None = None,
        headers: dict | None = None,
    ) -> Response:
        if query:
            url = self._prepare_url(url, query)
        response = await self.client.post(
            url,
            content=self._get_body(data),
            headers=self._get_updated_headers(headers),
        )
        return response

    async def put(
        self,
        url: str,
        data: dict | None = None,
        query: dict | None = None,
        headers: dict | None = None,
    ) -> Response:
        if query:
            url = self._prepare_url(url, query)
        response = await self.client.put(
            url,
            content=self._get_body(data),
            headers=self._get_updated_headers(headers),
        )
        return response

    async def get(
        self,
        url: str,
        query: dict | None = None,
        headers: dict | None = None,
    ) -> Response:
        if query:
            url = self._prepare_url(url, query)
        response = await self.client.get(
            url, headers=self._get_updated_headers(headers)
        )
        return response

    async def delete(
        self,
        url: str,
        query: dict | None = None,
        headers: dict | None = None,
    ) -> Response:
        if query:
            url = self._prepare_url(url, query)
        response = await self.client.delete(
            url, headers=self._get_updated_headers(headers)
        )
        return response

    async def login(self, url: str, email: str, password: str, device_id:str|None=None):
        response = await self.post(
            url,
            data={"email": email, "password": password, "device_id": device_id},
        )
        assert response.status_code == 200, response.json()
        access_token = response.json()["result"]["token"]["accessToken"]
        token_type = response.json()["result"]["token"]["tokenType"]
        self.headers["Authorization"] = f"{token_type} {access_token}"
        return response

    async def logout(self):
        self.headers = {}
