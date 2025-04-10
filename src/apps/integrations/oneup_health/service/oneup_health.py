import uuid
from datetime import datetime, timezone
from functools import reduce

import httpx

from apps.integrations.oneup_health.errors import (
    OneUpHealthAPIError,
    OneUpHealthAPIErrorMessageMap,
    OneUpHealthAPIForbiddenError,
    OneUpHealthUserAlreadyExists,
)
from apps.integrations.oneup_health.service.domain import EHRData
from apps.integrations.oneup_health.service.ehr_storage import EHRStorage
from apps.shared.exception import InternalServerError
from apps.subjects.domain import Subject
from config import settings

__all__ = ["OneupHealthService"]

from infrastructure.logger import logger


class OneupHealthAPIClient:
    def __init__(self):
        if settings.oneup_health.client_id is None or settings.oneup_health.client_secret is None:
            raise InternalServerError("OneUp health settings not configured")

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
                logger.error(f"Error requesting to OneUp health API {url_path} - {resp.status_code} {resp.text}")
                if resp.status_code == 403:
                    raise OneUpHealthAPIForbiddenError()
                raise OneUpHealthAPIError(resp.text)

            result = resp.json()
            if result.get("success") is False:
                logger.warn(f"Unsuccessful requesting to OneUp health API {url_path} - {result.get('error')}")
                raise OneUpHealthAPIErrorMessageMap.get(result.get("error"), OneUpHealthAPIError)()

            return result

    async def post_auth(self, url_path, data=None):
        async with httpx.AsyncClient(base_url=self._auth_base_url) as client:
            resp = await client.post(url=url_path, data={**data, **self._default_headers})
            if resp.status_code != 201 and resp.status_code != 400 and resp.status_code != 200:
                logger.error(f"Error requesting to OneUp health API {url_path} - {resp.status_code} {resp.text}")
                if resp.status_code == 403:
                    raise OneUpHealthAPIForbiddenError()
                raise OneUpHealthAPIError(resp.text)

            result = resp.json()

            return result

    async def get(self, url_path, params=None, headers=None):
        async with httpx.AsyncClient(base_url=self._base_url, headers=self._default_headers) as client:
            resp = await client.get(url=url_path, params=params, headers={**headers, **self._default_headers})
            if resp.status_code != 400 and resp.status_code != 200:
                logger.error(f"Error requesting to OneUp health API {url_path} - {resp.status_code} {resp.text}")
                if resp.status_code == 403:
                    raise OneUpHealthAPIForbiddenError()
                raise OneUpHealthAPIError()

            result = resp.json()
            if result.get("success") is False:
                logger.warn(f"Unsuccessful requesting to OneUp health API {url_path} - {result.get('error')}")
                raise OneUpHealthAPIErrorMessageMap.get(result.get("error"), OneUpHealthAPIError)()

            return result


class OneupHealthService:
    def __init__(self):
        self._client = OneupHealthAPIClient()

    async def _generate_auth_code(self, subject_id: uuid.UUID) -> str:
        result = await self._client.post("/user-management/v1/user/auth-code", params={"app_user_id": str(subject_id)})

        code = result.get("code")
        return code

    async def _get_token(self, code: str) -> dict[str, str]:
        result = await self._client.post_auth("/oauth2/token", data={"code": code, "grant_type": "authorization_code"})

        access_token = result.get("access_token")
        refresh_token = result.get("refresh_token")

        return dict(access_token=access_token, refresh_token=refresh_token)

    async def _get_user_id(self, subject_id: uuid.UUID):
        result = await self._client.get("/user-management/v1/user", params={"app_user_id": str(subject_id)})

        entries = result.get("entry", [])
        if len(entries) == 0:
            return None

        oneup_user_id = entries[0].get("oneup_user_id")

        return oneup_user_id

    async def create_user(self, subject_id: uuid.UUID) -> dict[str, str]:
        try:
            result = await self._client.post("/user-management/v1/user", params={"app_user_id": str(subject_id)})
            return {"oneup_user_id": result["oneup_user_id"], "code": result["code"]}
        except OneUpHealthUserAlreadyExists:
            if oneup_user_id := await self._get_user_id(subject_id=subject_id):
                return {"oneup_user_id": oneup_user_id}
            raise

    async def retrieve_token(self, subject_id: uuid.UUID, code: str | None = None):
        if not code:
            code = await self._generate_auth_code(subject_id)

        assert code
        return await self._get_token(code)

    async def check_for_transfer_initiated(self, oneup_user_id: int, start_date: datetime) -> bool:
        if oneup_user_id is None:
            return False

        try:
            result = await self._client.get(
                "/r4/AuditEvent",
                params={
                    "subtype": "data-transfer-initiated",
                    "recorded": f"ge{start_date.isoformat()}",
                    "agent-name:contains": f"1up-user-{oneup_user_id}",
                },
                headers={"x-oneup-user-id": str(oneup_user_id)},
            )

            if result.get("total") == 0:
                return False

            entries = result.get("entry", [])
            return len(entries) > 0
        except OneUpHealthAPIError as ex:
            logger.error(ex.message)

            return False

    async def check_for_transfer_completed(self, oneup_user_id: int, start_date: datetime) -> bool:
        if oneup_user_id is None:
            return False

        result = await self._client.get(
            "/r4/AuditEvent",
            params={
                "subtype": "member-data-ingestion-completed",
                "recorded": f"ge{start_date.isoformat()}",
                "agent-name:contains": f"1up-user-{oneup_user_id}",
            },
            headers={"x-oneup-user-id": str(oneup_user_id)},
        )

        if result.get("total", 0) == 0:
            return False

        logger.info("Transfer completed")

        return True

    async def check_for_transfer_timeout(self, oneup_user_id: int, start_date: datetime) -> bool:
        if oneup_user_id is None:
            return False

        result = await self._client.get(
            "/r4/AuditEvent",
            params={
                "subtype": "member-data-ingestion-timeout",
                "recorded": f"ge{start_date.isoformat()}",
                "agent-name:contains": f"1up-user-{oneup_user_id}",
            },
            headers={"x-oneup-user-id": str(oneup_user_id)},
        )

        if result.get("total", 0) == 0:
            return False

        logger.info("Transfer timeout detected")
        return True

    async def _get_resources(self, entry_url: str, oneup_user_id: int):
        result = await self._client.get(entry_url, headers={"x-oneup-user-id": str(oneup_user_id)})

        if result.get("total") == 0:
            return []

        logger.info(f"Retrieved {result.get('total')} resources from {entry_url}")

        entries = result.get("entry", [])
        resources = reduce(lambda acc, entry: acc + [entry.get("resource", {})], entries, [])

        links = result.get("link", [])
        next_page = next((link for link in links if link.get("relation") == "next"), None)
        if next_page is not None:
            resources += await self._get_resources(next_page.get("url"), oneup_user_id)

        return resources

    async def get_patient_data(self, session, subject: Subject) -> bool:
        oneup_user_id = subject.meta.get("oneup_user_id") if subject.meta else None
        if oneup_user_id is None:
            return False

        result = await self._client.get(
            "/r4/Patient",
            headers={"x-oneup-user-id": str(oneup_user_id)},
        )

        if result.get("total") == 0:
            return False

        entries = result.get("entry", [])
        for entry in entries:
            resource_url = entry.get("fullUrl")
            if resource_url:
                logger.info(f"Retrieving resources from {resource_url}")
                resources = await self._get_resources(f"{resource_url}/$everything", oneup_user_id)
                if len(resources) > 0:
                    healthcare_provider_id = entry.get("resource", {}).get("id")
                    ehr_storage = EHRStorage(session=session, applet_id=subject.applet_id)
                    data = EHRData(
                        resources=resources,
                        healthcare_provider_id=healthcare_provider_id,
                        date=datetime.now(timezone.utc),
                    )

                    await ehr_storage.upload(subject.id, data)
                    logger.info(f"Stored EHR data healthcare provider {healthcare_provider_id}")

        return True
