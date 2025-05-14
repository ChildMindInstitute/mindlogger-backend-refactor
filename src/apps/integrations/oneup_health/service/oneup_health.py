import hashlib
import uuid
from datetime import datetime, timezone
from functools import reduce

import httpx

from apps.integrations.oneup_health.errors import (
    OneUpHealthAPIError,
    OneUpHealthAPIErrorMessageMap,
    OneUpHealthAPIForbiddenError,
    OneUpHealthServiceUnavailableError,
    OneUpHealthTokenExpiredError,
    OneUpHealthUserAlreadyExists,
)
from apps.integrations.oneup_health.service.domain import EHRData
from apps.integrations.oneup_health.service.ehr_storage import create_ehr_storage
from apps.shared.exception import InternalServerError
from config import settings

__all__ = ["OneupHealthService"]

from infrastructure.logger import logger


def get_unique_short_id(submit_id: uuid.UUID, activity_id: uuid.UUID | None) -> str:
    full_unique_id = f"{submit_id}_{activity_id}"

    return hashlib.sha1(full_unique_id.encode()).hexdigest()


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

    @staticmethod
    def _handle_error(resp, url_path):
        """
        Handle errors returned by the OneUp Health API.

        The API should return a 400 status code if the request body is invalid,
        a 403 status code if the API key is invalid or the request is rate-limited,
        and a 201 status code if the request is successful.

        Args:
            resp (httpx.Response): The response returned by the API.
            url_path (str): The path of the API endpoint that the request was sent to.

        Raises:
            OneUpHealthAPIForbiddenError: If the API returns a 403 status code.
            OneUpHealthServiceUnavailableError: If the API returns a 503 or 504 status code.
            OneUpHealthTokenExpiredError: If the API returns a 401 status code.
            OneUpHealthAPIError: If the API returns any other error status code.
        """
        if resp.status_code not in (200, 201, 400):
            # Log all errors with detailed information
            logger.error(
                "1UpHealth API error",
                extra={
                    "error_type": "oneup_health_api_error",
                    "status_code": resp.status_code,
                    "url_path": url_path,
                    "response_text": resp.text[:500] if resp.text else None,
                },
            )

            if resp.status_code == 401:
                # The API returns a 401 status code if the token has expired
                logger.error(
                    "1UpHealth token expired",
                    extra={
                        "error_type": "oneup_health_token_expired",
                        "url_path": url_path,
                    },
                )
                raise OneUpHealthTokenExpiredError()

            elif resp.status_code == 403:
                # The API returns a 403 status code if request comes from outside the USA
                logger.error(
                    "1UpHealth geographic restriction",
                    extra={
                        "error_type": "oneup_health_geo_restricted",
                        "url_path": url_path,
                    },
                )
                raise OneUpHealthAPIForbiddenError()

            elif resp.status_code in (503, 504):
                # The API returns 503 or 504 status codes if the service is unavailable
                logger.error(
                    "1UpHealth service unavailable",
                    extra={
                        "error_type": "oneup_health_service_unavailable",
                        "status_code": resp.status_code,
                        "url_path": url_path,
                    },
                )
                raise OneUpHealthServiceUnavailableError()

            # The API should return a 400 status code if the request body is invalid.
            logger.error(
                "1UpHealth API error",
                extra={
                    "error_type": "oneup_health_api_error",
                    "status_code": resp.status_code,
                    "url_path": url_path,
                    "response_text": resp.text[:500] if resp.text else None,
                },
            )
            raise OneUpHealthAPIError(resp.text)

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
        try:
            async with httpx.AsyncClient(base_url=self._base_url, headers=self._default_headers) as client:
                resp = await client.post(url=url_path, data=data, params=params)
                OneupHealthAPIClient._handle_error(resp, url_path)

                result = resp.json()
                if result.get("success") is False:
                    logger.warning(f"Unsuccessful requesting to OneUp health API {url_path} - {result.get('error')}")
                    raise OneUpHealthAPIErrorMessageMap.get(result.get("error"), OneUpHealthAPIError)()

                return result
        except httpx.RequestError as e:
            logger.error(f"Error requesting to OneUp health API {url_path} - {str(e)}", exc_info=True)
            raise OneUpHealthAPIError()

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
        try:
            async with httpx.AsyncClient(base_url=self._auth_base_url) as client:
                resp = await client.post(url=url_path, data={**data, **self._default_headers})
                OneupHealthAPIClient._handle_error(resp, url_path)

                result = resp.json()

                return result
        except httpx.RequestError as e:
            logger.error(f"Error requesting to OneUp health API {url_path} - {str(e)}", exc_info=True)
            raise OneUpHealthAPIError()

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
        try:
            async with httpx.AsyncClient(base_url=self._base_url, headers=self._default_headers) as client:
                resp = await client.get(
                    url=url_path, params=params, headers={**(headers if headers else {}), **self._default_headers}
                )
                logger.info(f"Requesting to OneUp health API {url_path} - {resp.status_code}")
                OneupHealthAPIClient._handle_error(resp, url_path)

                result = resp.json()
                if result.get("success") is False:
                    logger.warning(f"Unsuccessful requesting to OneUp health API {url_path} - {result.get('error')}")
                    raise OneUpHealthAPIErrorMessageMap.get(result.get("error"), OneUpHealthAPIError)()

                return result
        except httpx.RequestError as e:
            logger.error(f"Error requesting to OneUp health API {url_path} - {str(e)}", exc_info=True)
            raise OneUpHealthAPIError()


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

    async def _generate_auth_code(self, submit_id: uuid.UUID, activity_id: uuid.UUID | None = None) -> str:
        """
        Generate an authentication code for a subject.

        Args:
            submit_id (uuid.UUID): The unique identifier for the submission.
            activity_id (uuid.UUID | None): The unique identifier for the activity.

        Returns:
            str: The generated authentication code.

        Raises:
            OneUpHealthAPIError: If the API request fails.
        """
        app_user_id = get_unique_short_id(submit_id=submit_id, activity_id=activity_id)
        result = await self._client.post("/user-management/v1/user/auth-code", params={"app_user_id": app_user_id})

        return result.get("code")

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

    async def get_oneup_user_id(self, submit_id: uuid.UUID, activity_id: uuid.UUID | None = None) -> int | None:
        """
        Get the OneUp Health user ID

        Args:
            submit_id (uuid.UUID): The unique identifier for the submission.
            activity_id (uuid.UUID, optional): The unique identifier for the activity.

        Returns:
            int or None: The OneUp Health user ID if found, None otherwise.

        Raises:
            OneUpHealthAPIError: If the API request fails.
        """
        app_user_id = get_unique_short_id(submit_id=submit_id, activity_id=activity_id)
        result = await self._client.get("/user-management/v1/user", params={"app_user_id": app_user_id})

        entries = result.get("entry", [])
        if len(entries) == 0:
            return None

        oneup_user_id = entries[0].get("oneup_user_id")

        return oneup_user_id

    async def create_user(self, submit_id: uuid.UUID, activity_id: uuid.UUID | None = None) -> dict[str, str]:
        """
        Create a new user in the OneUp Health platform or retrieve an existing user.

        Args:
            submit_id (uuid.UUID): The unique identifier for the submission.
            activity_id (uuid.UUID, optional): The unique identifier for the activity.

        Returns:
            dict: A dictionary containing the oneup_user_id and optionally a code.

        Raises:
            OneUpHealthAPIError: If the API request fails and the user doesn't already exist.
        """
        try:
            app_user_id = get_unique_short_id(submit_id=submit_id, activity_id=activity_id)
            result = await self._client.post("/user-management/v1/user", params={"app_user_id": app_user_id})
            return {"oneup_user_id": result["oneup_user_id"], "code": result["code"]}
        except OneUpHealthUserAlreadyExists:
            oneup_user_id = await self.get_oneup_user_id(submit_id=submit_id, activity_id=activity_id)
            if oneup_user_id is not None:
                return {"oneup_user_id": str(oneup_user_id)}
            raise

    async def retrieve_token(self, submit_id: uuid.UUID, activity_id: uuid.UUID | None = None, code: str | None = None):
        """
        Retrieve access and refresh tokens for a user.

        If no code is provided, a new authentication code will be generated.

        Args:
            submit_id (uuid.UUID): The unique identifier for the submission.
            activity_id (uuid.UUID, optional): The unique identifier for the activity.
            code (str, optional): An existing authentication code to use.

        Returns:
            dict: A dictionary containing the access_token and refresh_token.

        Raises:
            OneUpHealthAPIError: If the API request fails.
            AssertionError: If no code is available.
        """
        app_user_id = get_unique_short_id(submit_id=submit_id, activity_id=activity_id)
        if not code:
            code = await self._generate_auth_code(submit_id, activity_id)

        assert code
        return {**await self._get_token(code), "app_user_id": app_user_id}

    async def refresh_token(self, refresh_token: str) -> dict[str, str]:
        """
        Refresh an access token using a refresh token.

        Args:
            refresh_token (str): The refresh token to use for getting a new access token.

        Returns:
            dict: A dictionary containing the new access_token and refresh_token.

        Raises:
            OneUpHealthAPIError: If the API request fails.
        """
        result = await self._client.post_auth(
            "/oauth2/token", data={"refresh_token": refresh_token, "grant_type": "refresh_token"}
        )

        access_token = result.get("access_token")
        new_refresh_token = result.get("refresh_token")

        return dict(access_token=access_token, refresh_token=new_refresh_token)

    async def check_audit_events(self, oneup_user_id: int, start_date: datetime | None) -> dict[str, int]:
        """
        Check if a data transfer h

        Args:
            oneup_user_id (int): The OneUp Health user ID to check.
            start_date (datetime): The date from which to start checking.

        Returns:
            int: The number of initiated transfers found, or 0 if none or if an error occurred.
        """
        counters = {"initiated": 0, "completed": 0, "timeout": 0}

        if oneup_user_id is None:
            return counters

        params = {
            "subtype": "data-transfer-initiated,member-data-ingestion-completed,member-data-ingestion-timeout",
            "agent-name:contains": f"1up-user-{oneup_user_id}",
        }

        if start_date is not None:
            params["recorded"] = f"ge{start_date.isoformat()}"

        try:
            result = await self._client.get(
                "/r4/AuditEvent",
                params=params,
                headers={"x-oneup-user-id": str(oneup_user_id)},
            )

            for entry in result.get("entry", []):
                subtypes = entry.get("resource", {}).get("subtype", [])
                for subtype in subtypes:
                    if subtype.get("code") == "data-transfer-initiated":
                        counters["initiated"] += 1
                        break
                    elif subtype.get("code") == "member-data-ingestion-completed":
                        counters["completed"] += 1
                        break
                    elif subtype.get("code") == "member-data-ingestion-timeout":
                        counters["timeout"] += 1
                        break

        except OneUpHealthAPIError as ex:
            logger.error(ex.message)

        return counters

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

        entries = result.get("entry", [])
        resources: list = reduce(lambda acc, entry: acc + [entry.get("resource", {})], entries, [])

        logger.debug(f"Retrieved {len(resources)} resources from {entry_url}")

        links = result.get("link", [])
        next_page = next((link for link in links if link.get("relation") == "next"), None)
        if next_page is not None:
            resources += await self._get_resources(next_page.get("url"), oneup_user_id)

        return resources

    async def retrieve_patient_data(
        self, session, applet_id: uuid.UUID, submit_id: uuid.UUID, activity_id: uuid.UUID, oneup_user_id: int
    ) -> str | None:
        """
        Retrieve and store patient data for a subject.

        This method fetches patient data from OneUp Health and stores it using the EHR storage.

        Args:
            session: The database session to use.
            applet_id (uuid.UUID): The unique identifier for the applet.
            submit_id (uuid.UUID): The unique identifier for the submission.
            activity_id (uuid.UUID): The unique identifier for the activity.
            oneup_user_id (int): The OneUp Health user ID

        Returns:
            bool: True if data was successfully retrieved and stored, False otherwise.
        """

        result = await self._client.get(
            "/r4/Patient",
            headers={"x-oneup-user-id": str(oneup_user_id)},
        )

        if result.get("total") == 0:
            return None

        storage_path = None
        entries = result.get("entry", [])
        for entry in entries:
            resource_url = entry.get("fullUrl")
            if resource_url:
                logger.info(f"Retrieving resources from {resource_url}")
                resources = await self._get_resources(f"{resource_url}/$everything?_count=100", oneup_user_id)
                if len(resources) > 0:
                    healthcare_provider_id = entry.get("resource", {}).get("id")
                    ehr_storage = await create_ehr_storage(session=session, applet_id=applet_id)
                    data = EHRData(
                        resources=resources,
                        healthcare_provider_id=healthcare_provider_id,
                        date=datetime.now(timezone.utc),
                        submit_id=submit_id,
                        activity_id=activity_id,
                    )

                    storage_path = await ehr_storage.upload_resources(data)
                    logger.info(f"Stored EHR data healthcare provider {healthcare_provider_id} in {storage_path}")

        return storage_path
