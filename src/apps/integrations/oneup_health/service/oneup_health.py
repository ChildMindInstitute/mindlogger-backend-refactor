import uuid

import httpx

from apps.shared.exception import InternalServerError
from config import settings

__all__ = ["OneupHealthService"]

from infrastructure.logger import logger


class OneupHealthAPIClient:
    def __init__(self):
        self._default_headers = {
            "client_id": settings.oneup_health.client_id,
            "client_secret": settings.oneup_health.client_secret,
        }
        self._base_url = settings.oneup_health.base_url
        self._auth_base_url = settings.oneup_health.auth_base_url

    async def post(self, url_path, data=None, params=None):
        async with httpx.AsyncClient(base_url=self._base_url, headers=self._default_headers) as client:
            resp = await client.post(url=url_path, data=data, params=params)
            if resp.status_code != 201 and resp.status_code != 400 and resp.status_code != 200:
                raise InternalServerError(resp.text)

            result = resp.json()

            logger.info(result)
            return result

    async def postAuth(self, url_path, data=None):
        async with httpx.AsyncClient(base_url=self._auth_base_url) as client:
            resp = await client.post(url=url_path, data={**data, **self._default_headers})
            if resp.status_code != 201 and resp.status_code != 400 and resp.status_code != 200:
                raise InternalServerError(resp.text)

            result = resp.json()

            logger.info(result)
            return result

    async def get(self, url_path, params=None):
        async with httpx.AsyncClient(base_url=self._base_url, headers=self._default_headers) as client:
            resp = await client.get(url=url_path, params=params)
            if resp.status_code != 201 and resp.status_code != 400 and resp.status_code != 200:
                raise InternalServerError(resp.text)

            return resp.json()


class OneupHealthService:
    def __init__(self, session, user):
        self._session = session
        self._user = user
        self._client = OneupHealthAPIClient()

    async def create_user(self, subject_id: uuid.UUID) -> dict[str, str]:
        result = await self._client.post("/user-management/v1/user", params={"app_user_id": str(subject_id)})
        if result["success"] is False:
            if result["error"] == "this user already exists":
                oneup_user_id = await self._get_user_id(subject_id=subject_id)
                return {"oneup_user_id": oneup_user_id}

            raise InternalServerError(result["error"])

        return {"oneup_user_id": result["oneup_user_id"], "code": result["code"]}

    async def _generate_auth_code(self, subject_id: uuid.UUID) -> str:
        result = await self._client.post("/user-management/v1/user/auth-code", params={"app_user_id": str(subject_id)})
        if result["success"] is False:
            raise InternalServerError(result["error"])

        code = result.get("code")
        return code

    async def _get_token(self, code: str) -> dict[str, str]:
        result = await self._client.postAuth("/oauth2/token", data={"code": code, "grant_type": "authorization_code"})

        access_token = result.get("access_token")
        refresh_token = result.get("refresh_token")

        return dict(access_token=access_token, refresh_token=refresh_token)

    async def _get_user_id(self, subject_id: uuid.UUID):
        result = await self._client.get("/user-management/v1/user", params={"app_user_id": str(subject_id)})

        if result["success"] is False:
            raise InternalServerError(result["error"])

        oneup_user_id = result.get("entry", [])[0].get("oneup_user_id")

        return oneup_user_id

    async def retrieve_token(self, subject_id: uuid.UUID, code: str | None = None):
        if not code:
            code = await self._generate_auth_code(subject_id)

        assert code
        return await self._get_token(code)
