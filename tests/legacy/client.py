import json
import urllib.parse
import uuid
from io import BytesIO
from typing import Any, Mapping

from httpx import ASGITransport, AsyncClient, Response
from pydantic import BaseModel

from apps.authentication.domain.token import JWTClaim
from apps.authentication.services import AuthenticationService
from apps.users.domain import User
from config import settings


class TestClient:
    def __init__(self, app) -> None:
        self.client = AsyncClient(transport=ASGITransport(app=app), base_url="http://test.com")
        self.headers: dict[str, Any] = {}

    @staticmethod
    def _prepare_url(url, query) -> str:
        return f"{url}?{urllib.parse.urlencode(query)}"

    def _get_updated_headers(self, headers: dict | None = None) -> dict:
        headers_ = dict(self.headers)
        if headers:
            headers_.update(headers)
        return headers_

    def _get_json_headers(
        self,
        headers: dict | None = None,
        body: str | None = None,
        files: Mapping[str, BytesIO] | None = None,
    ) -> dict:
        """Headers for a request whose body is serialized JSON.

        The body is passed to httpx as raw ``content``, so the JSON content type has to be set
        explicitly - Starlette will not parse the body into the endpoint's model without it.
        Skipped for multipart requests and when the caller sets the header itself.
        """
        headers_ = self._get_updated_headers(headers)
        if body is not None and not files and not any(k.lower() == "content-type" for k in headers_):
            headers_["Content-Type"] = "application/json"
        return headers_

    @staticmethod
    def _get_body(
        data: dict[str, Any] | BaseModel | list[dict[str, Any]] | list[BaseModel] | None = None,
    ) -> str | None:
        if data:
            if isinstance(data, BaseModel):
                request_data = data.model_dump()
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
        body = self._get_body(data)
        response = await self.client.post(
            url,
            content=body,
            headers=self._get_json_headers(headers, body, files),
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
        body = self._get_body(data)
        response = await self.client.put(
            url,
            content=body,
            headers=self._get_json_headers(headers, body),
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
        body = self._get_body(data)
        response = await self.client.request(
            "DELETE",
            url,
            content=body,
            headers=self._get_json_headers(headers, body),
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
