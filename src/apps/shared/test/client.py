import json
import urllib.parse
import uuid
from io import BytesIO
from typing import Any, Mapping

from httpx import AsyncClient, Response
from pydantic import BaseModel

from apps.authentication.domain.token import JWTClaim
from apps.authentication.services import AuthenticationService
from apps.users.domain import User
from config import settings


class TestClient:
    def __init__(self, app) -> None:
        self.client = AsyncClient(app=app, base_url="http://test.com")
        self.headers: dict[str, Any] = {}

    @staticmethod
    def _prepare_url(url, query) -> str:
        return f"{url}?{urllib.parse.urlencode(query)}"

    def _get_updated_headers(self, headers: dict | None = None) -> dict:
        headers_ = dict(self.headers)
        if headers:
            headers_.update(headers)
        return headers_

    @staticmethod
    def _get_body(
        data: dict[str, Any] | BaseModel | list[dict[str, Any]] | list[BaseModel] | None = None,
    ) -> str | None:
        if data:
            if isinstance(data, BaseModel):
                request_data = data.dict()
            else:
                request_data = data  # type: ignore[assignment]
            return json.dumps(request_data, default=str)
        return None

    async def post(
        self,
        url: str,
        data: dict[str, Any] | BaseModel | list[dict[str, Any]] | list[BaseModel] | None = None,
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
        data: dict | BaseModel | None = None,
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

    def login(self, user: User | uuid.UUID):
        if isinstance(user, User):
            sub = user.id
        else:
            sub = user
        access_token = AuthenticationService.create_access_token(
            {
                JWTClaim.sub: str(sub),
                JWTClaim.rjti: str(uuid.uuid4()),
            }
        )
        self.headers["Authorization"] = f"{settings.authentication.token_type} {access_token}"

    def logout(self) -> None:
        self.headers = {}
