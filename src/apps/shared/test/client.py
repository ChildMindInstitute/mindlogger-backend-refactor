import json
import urllib.parse
from io import BytesIO
from typing import Any, Mapping, Type, TypeVar

from httpx import AsyncClient, Response
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class TestClient:
    def __init__(self, app):
        self.client = AsyncClient(app=app, base_url="http://test.com")
        self.headers = {}

    @staticmethod
    def _prepare_url(url, query):
        return f"{url}?{urllib.parse.urlencode(query)}"

    def _get_updated_headers(self, headers: dict | None = None) -> dict:
        headers_ = dict(self.headers)
        if headers:
            headers_.update(headers)
        return headers_

    @staticmethod
    def _get_body(data: dict[str, Any] | Type[T] | None = None):
        if data:
            if isinstance(data, BaseModel):
                request_data = data.dict()
            else:
                request_data = data
            return json.dumps(request_data, default=str)
        return None

    async def post(
        self,
        url: str,
        data: dict[str, Any] | Type[T] | None = None,
        query: dict | None = None,
        headers: dict | None = None,
        files: Mapping[str, BytesIO] | None = None,
    ) -> Response:
        if query:
            url = self._prepare_url(url, query)
        response = await self.client.post(
            url,
            content=self._get_body(data),
            headers=self._get_updated_headers(headers),
            files=files,
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
        response = await self.client.get(url, headers=self._get_updated_headers(headers))
        return response

    async def delete(
        self,
        url: str,
        data: dict | None = None,
        query: dict | None = None,
        headers: dict | None = None,
    ) -> Response:
        if query:
            url = self._prepare_url(url, query)
        response = await self.client.request(
            "DELETE",
            url,
            content=self._get_body(data),
            headers=self._get_updated_headers(headers),
        )
        return response

    async def login(self, url: str, email: str | None, password: str, device_id: str | None = None):
        # Just make password option to shut up mypy error when User.email_encrypted passed as arument
        assert password is not None
        response = await self.post(
            url,
            data={
                "email": email,
                "password": password,
                "device_id": device_id,
            },
        )
        assert response.status_code == 200, response.json()
        access_token = response.json()["result"]["token"]["accessToken"]
        token_type = response.json()["result"]["token"]["tokenType"]
        self.headers["Authorization"] = f"{token_type} {access_token}"
        return response

    async def logout(self):
        self.headers = {}
