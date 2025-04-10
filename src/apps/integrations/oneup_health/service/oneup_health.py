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
    """
    Client for interacting with the OneUp Health API.
    
    This class provides methods to make HTTP requests to the OneUp Health API,
    handling authentication, error responses, and response parsing.
    
    Raises:
        InternalServerError: If OneUp Health settings are not configured.
    """
    
    def __init__(self):
        """
        Initialize the OneUp Health API client.
        
        Validates that required configuration settings are present and sets up
        the default headers and base URLs for API requests.
        
        Raises:
            InternalServerError: If client_id or client_secret is not configured.
        """
        if settings.oneup_health.client_id is None or settings.oneup_health.client_secret is None:
            raise InternalServerError("OneUp health settings not configured")

        self._default_headers = {
            "client_id": settings.oneup_health.client_id,
            "client_secret": settings.oneup_health.client_secret,
        }
        self._base_url = settings.oneup_health.base_url
        self._auth_base_url = settings.oneup_health.auth_base_url

    async def post(self, url_path, data=None, params=None):
        """
        Send a POST request to the OneUp Health API.
        
        Args:
            url_path (str): The API endpoint path to send the request to.
            data (dict, optional): The data to send in the request body.
            params (dict, optional): The query parameters to include in the request.
            
        Returns:
            dict: The JSON response from the API.
            
        Raises:
            OneUpHealthAPIForbiddenError: If the API returns a 403 status code.
            OneUpHealthAPIError: If the API returns any other error status code or an unsuccessful response.
        """
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
        """
        Send a POST request to the OneUp Health authentication API.
        
        Args:
            url_path (str): The authentication API endpoint path.
            data (dict, optional): The data to send in the request body.
            
        Returns:
            dict: The JSON response from the API.
            
        Raises:
            OneUpHealthAPIForbiddenError: If the API returns a 403 status code.
            OneUpHealthAPIError: If the API returns any other error status code.
        """
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
        """
        Send a GET request to the OneUp Health API.
        
        Args:
            url_path (str): The API endpoint path to send the request to.
            params (dict, optional): The query parameters to include in the request.
            headers (dict, optional): Additional headers to include in the request.
            
        Returns:
            dict: The JSON response from the API.
            
        Raises:
            OneUpHealthAPIForbiddenError: If the API returns a 403 status code.
            OneUpHealthAPIError: If the API returns any other error status code or an unsuccessful response.
        """
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
    """
    Service for interacting with the OneUp Health platform.
    
    This service provides methods to manage users, retrieve tokens, check transfer status,
    and fetch patient data from the OneUp Health platform.
    """
    
    def __init__(self):
        """
        Initialize the OneUp Health service with an API client.
        """
        self._client = OneupHealthAPIClient()

    async def _generate_auth_code(self, subject_id: uuid.UUID) -> str:
        """
        Generate an authentication code for a subject.
        
        Args:
            subject_id (uuid.UUID): The ID of the subject to generate the code for.
            
        Returns:
            str: The generated authentication code.
            
        Raises:
            OneUpHealthAPIError: If the API request fails.
        """
        result = await self._client.post("/user-management/v1/user/auth-code", params={"app_user_id": str(subject_id)})

        code = result.get("code")
        return code

    async def _get_token(self, code: str) -> dict[str, str]:
        """
        Exchange an authentication code for access and refresh tokens.
        
        Args:
            code (str): The authentication code to exchange.
            
        Returns:
            dict: A dictionary containing the access_token and refresh_token.
            
        Raises:
            OneUpHealthAPIError: If the API request fails.
        """
        result = await self._client.post_auth("/oauth2/token", data={"code": code, "grant_type": "authorization_code"})

        access_token = result.get("access_token")
        refresh_token = result.get("refresh_token")

        return dict(access_token=access_token, refresh_token=refresh_token)

    async def _get_user_id(self, subject_id: uuid.UUID):
        """
        Get the OneUp Health user ID for a subject.
        
        Args:
            subject_id (uuid.UUID): The ID of the subject to get the user ID for.
            
        Returns:
            int or None: The OneUp Health user ID if found, None otherwise.
            
        Raises:
            OneUpHealthAPIError: If the API request fails.
        """
        result = await self._client.get("/user-management/v1/user", params={"app_user_id": str(subject_id)})

        entries = result.get("entry", [])
        if len(entries) == 0:
            return None

        oneup_user_id = entries[0].get("oneup_user_id")

        return oneup_user_id

    async def create_user(self, subject_id: uuid.UUID) -> dict[str, str]:
        """
        Create a new user in the OneUp Health platform or retrieve an existing user.
        
        Args:
            subject_id (uuid.UUID): The ID of the subject to create a user for.
            
        Returns:
            dict: A dictionary containing the oneup_user_id and optionally a code.
            
        Raises:
            OneUpHealthAPIError: If the API request fails and the user doesn't already exist.
        """
        try:
            result = await self._client.post("/user-management/v1/user", params={"app_user_id": str(subject_id)})
            return {"oneup_user_id": result["oneup_user_id"], "code": result["code"]}
        except OneUpHealthUserAlreadyExists:
            if oneup_user_id := await self._get_user_id(subject_id=subject_id):
                return {"oneup_user_id": oneup_user_id}
            raise

    async def retrieve_token(self, subject_id: uuid.UUID, code: str | None = None):
        """
        Retrieve access and refresh tokens for a subject.
        
        If no code is provided, a new authentication code will be generated.
        
        Args:
            subject_id (uuid.UUID): The ID of the subject to retrieve tokens for.
            code (str, optional): An existing authentication code to use.
            
        Returns:
            dict: A dictionary containing the access_token and refresh_token.
            
        Raises:
            OneUpHealthAPIError: If the API request fails.
            AssertionError: If no code is available.
        """
        if not code:
            code = await self._generate_auth_code(subject_id)

        assert code
        return await self._get_token(code)

    async def check_for_transfer_initiated(self, oneup_user_id: int, start_date: datetime) -> int:
        """
        Check if a data transfer has been initiated for a user.
        
        Args:
            oneup_user_id (int): The OneUp Health user ID to check.
            start_date (datetime): The date from which to start checking.
            
        Returns:
            int: The number of initiated transfers found, or 0 if none or if an error occurred.
        """
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

            return result.get("total", 0)

        except OneUpHealthAPIError as ex:
            logger.error(ex.message)

            return 0

    async def check_for_transfer_completed(self, oneup_user_id: int, start_date: datetime) -> int:
        """
        Check if a data transfer has been completed for a user.
        
        Args:
            oneup_user_id (int): The OneUp Health user ID to check.
            start_date (datetime): The date from which to start checking.
            
        Returns:
            int: The number of completed transfers found, or 0 if none.
        """
        if oneup_user_id is None:
            return 0

        result = await self._client.get(
            "/r4/AuditEvent",
            params={
                "subtype": "member-data-ingestion-completed",
                "recorded": f"ge{start_date.isoformat()}",
                "agent-name:contains": f"1up-user-{oneup_user_id}",
            },
            headers={"x-oneup-user-id": str(oneup_user_id)},
        )

        if total := result.get("total", 0) > 0:
            logger.info(f"{total} Transfers completed")

        return total

    async def check_for_transfer_timeout(self, oneup_user_id: int, start_date: datetime) -> int:
        """
        Check if a data transfer has timed out for a user.
        
        Args:
            oneup_user_id (int): The OneUp Health user ID to check.
            start_date (datetime): The date from which to start checking.
            
        Returns:
            int: The number of timed-out transfers found, or 0 if none.
        """
        if oneup_user_id is None:
            return 0

        result = await self._client.get(
            "/r4/AuditEvent",
            params={
                "subtype": "member-data-ingestion-timeout",
                "recorded": f"ge{start_date.isoformat()}",
                "agent-name:contains": f"1up-user-{oneup_user_id}",
            },
            headers={"x-oneup-user-id": str(oneup_user_id)},
        )

        if total := result.get("total", 0) > 0:
            logger.info(f"{total} Transfers timeout detected")

        return total

    async def _get_resources(self, entry_url: str, oneup_user_id: int):
        """
        Recursively retrieve resources from a OneUp Health API endpoint.
        
        This method handles pagination by following the 'next' link in the response.
        
        Args:
            entry_url (str): The URL to retrieve resources from.
            oneup_user_id (int): The OneUp Health user ID to use in the request.
            
        Returns:
            list: A list of resource objects.
        """
        
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
        """
        Retrieve and store patient data for a subject.
        
        This method fetches patient data from OneUp Health and stores it using the EHR storage.
        
        Args:
            session: The database session to use.
            subject (Subject): The subject to retrieve data for.
            
        Returns:
            bool: True if data was successfully retrieved and stored, False otherwise.
        """
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
