import base64
import hashlib
import io
import mimetypes
import uuid
import zipfile
from datetime import datetime, timezone
from functools import reduce

import httpx
from slugify import slugify

from apps.integrations.oneup_health.errors import (
    OneUpHealthAPIError,
    OneUpHealthAPIErrorMessageMap,
    OneUpHealthAPIForbiddenError,
    OneUpHealthServiceUnavailableError,
    OneUpHealthTokenExpiredError,
    OneUpHealthUserAlreadyExistsError,
)
from apps.integrations.oneup_health.service.domain import EHRData, EHRFileMetadata, EHRFileTypeEnum, EHRMetadata
from apps.integrations.oneup_health.service.ehr_storage import EHRStorage, create_ehr_storage
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
        Handle errors returned by the 1UpHealth API.

        The API should return a 400 status code if the request body is invalid,
        a 403 status code if the API key is invalid or the request is rate-limited,
        and a 201 status code if the request is successful.

        1UpHealth API returns the following error codes that are currently being mapped:
        - 400: 1UpHealth request failed. Reasons are varied. Currently, we're only handling "this user already exists".
        - 401: 1UpHealth token expired
        - 403: Forbidden access to 1UpHealth API. This is due to the user being outside the United States.
        - 503, 504: 1UpHealth service unavailable

        Args:
            resp (httpx.Response): The response returned by the API.
            url_path (str): The path of the API endpoint that the request was sent to.

        Raises:
            OneUpHealthAPIError: If the API returns any other error status code.
            OneUpHealthUserAlreadyExistsError: If the API returns a 400 status code with a
                "this user already exists" error.
            OneUpHealthTokenExpiredError: If the API returns a 401 status code.
            OneUpHealthAPIForbiddenError: If the API returns a 403 status code.
            OneUpHealthServiceUnavailableError: If the API returns a 503 or 504 status code.
        """
        if resp.status_code not in (200, 201):
            if resp.status_code == 400 and (resp.json() and resp.json().get("error") == "this user already exists"):
                # The API returns a 400 status code with a "this user already exists" error if the user already exists
                logger.error(
                    f"1UpHealth user already exists - Path: {url_path} - Status: {resp.status_code}",
                    extra={
                        "error_type": "oneup_health_user_already_exists",
                        "status_code": resp.status_code,
                        "url_path": url_path,
                    },
                )
                raise OneUpHealthUserAlreadyExistsError()

            if resp.status_code == 401:
                # The API returns a 401 status code if the token has expired
                logger.error(
                    f"1UpHealth token expired - Path: {url_path} - Status: {resp.status_code}",
                    extra={
                        "error_type": "oneup_health_token_expired",
                        "url_path": url_path,
                        "status_code": resp.status_code,
                    },
                )
                raise OneUpHealthTokenExpiredError()

            elif resp.status_code == 403:
                # The API returns a 403 status code if request comes from outside the USA
                logger.error(
                    f"1UpHealth geographic restriction - Path: {url_path} - Status: {resp.status_code}",
                    extra={
                        "error_type": "oneup_health_geo_restricted",
                        "url_path": url_path,
                        "status_code": resp.status_code,
                    },
                )
                raise OneUpHealthAPIForbiddenError()

            elif resp.status_code in (503, 504):
                # The API returns 503 or 504 status codes if the service is unavailable
                logger.error(
                    f"1UpHealth service unavailable - Path: {url_path} - Status: {resp.status_code}",
                    extra={
                        "error_type": "oneup_health_service_unavailable",
                        "status_code": resp.status_code,
                        "url_path": url_path,
                    },
                )
                raise OneUpHealthServiceUnavailableError()

            # For any other error status code
            response_text = resp.text[:200] if resp.text else "No response text"
            logger.error(
                f"1UpHealth API error - Path: {url_path} - Status: {resp.status_code} - Response: {response_text}",
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

    async def create_or_retrieve_user(
        self, submit_id: uuid.UUID, activity_id: uuid.UUID | None = None
    ) -> dict[str, str]:
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
        except OneUpHealthUserAlreadyExistsError:
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
            dict: A dictionary containing the access_token, the refresh_token, and the app_user_id.

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
            dict: A dictionary containing the new access_token and refresh_token

        Raises:
            OneUpHealthAPIError: If the API request fails.
        """
        result = await self._client.post_auth(
            "/oauth2/token", data={"refresh_token": refresh_token, "grant_type": "refresh_token"}
        )

        access_token = result.get("access_token")
        new_refresh_token = result.get("refresh_token")

        return dict(access_token=access_token, refresh_token=new_refresh_token)

    async def check_audit_events(
        self, oneup_user_id: int, start_date: datetime | None
    ) -> tuple[dict[str, int], list[dict[str, str]]]:
        """
        Check if a data transfer h

        Args:
            oneup_user_id (int): The OneUp Health user ID to check.
            start_date (datetime): The date from which to start checking.

        Returns:
            int: The number of initiated transfers found, or 0 if none or if an error occurred.
        """
        counters = {"initiated": 0, "completed": 0, "timeout": 0}
        healthcare_providers = []

        if oneup_user_id is None:
            return counters, healthcare_providers

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
                # Get the healthcare providers data
                agents = entry.get("resource", {}).get("agent", [])
                for agent in agents:
                    coding = agent.get("type", {}).get("coding", [])
                    if len(coding) > 0 and coding[0].get("code") == "CST":
                        healthcare_providers.append(dict(name=agent.get("name"), id=agent.get("altId")))
                # Count the audit events
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

        return counters, healthcare_providers

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

    def _get_document_references(self, resource_list) -> list[dict[str, str]]:
        """Filter DocumentReference resources and extract their document URLs."""
        doc_refs = [res for res in resource_list if res.get("resourceType") == "DocumentReference"]
        documents = []
        for doc_ref in doc_refs:
            for content in doc_ref.get("content", []):
                attachment = content.get("attachment", {})
                title = attachment.get("title")
                url = attachment.get("url")
                if url:
                    documents.append(dict(title=title, url=url))
        return documents

    def _get_extension_from_content_type(self, content_type: str) -> str | None:
        """Return the file extension (with dot) for a given MIME content type, or None if unknown."""
        # Handle common edge cases if needed
        if content_type == "application/xml":
            return ".xml"

        if content_type == "application/json":
            return ".json"

        return mimetypes.guess_extension(content_type)

    async def _download_and_store_documents(
        self, ehr_storage, oneup_user_id: int, data: EHRData
    ) -> tuple[str | None, int | None]:
        document_references = self._get_document_references(data.resources)

        if len(document_references) == 0:
            logger.info(f"No documents found for activity_id {data.activity_id}, submit_id {data.submit_id}")
            return None, None

        base_path = f"{data.activity_id}/{data.submit_id}"
        zip_filename = EHRStorage.docs_zip_filename(data)

        # TODO: Optimize this function to avoid loading all files in memory when creating the zip file.
        # Current implementation loads all document content into memory before writing to the zip file,
        # which can cause memory issues with large documents or many documents.
        # Consider using a streaming approach or temporary files to reduce memory usage.
        zip_buffer = io.BytesIO()
        try:
            with zipfile.ZipFile(zip_buffer, "w", compression=zipfile.ZIP_DEFLATED) as zip_file:
                for reference in document_references:
                    url = reference["url"]
                    try:
                        document_meta = await self._client.get(url, headers={"x-oneup-user-id": str(oneup_user_id)})
                        title = reference.get("title")
                        last_updated_str = document_meta.get("meta", {}).get("lastUpdated")
                        date = (
                            datetime.fromisoformat(last_updated_str.replace("Z", "+00:00"))
                            if last_updated_str
                            else None
                        )
                        if date:
                            date_string = date.strftime("%Y%m%d_%H%M%S")
                        ext = self._get_extension_from_content_type(document_meta.get("contentType"))
                        logger.info(f"Guessed extension: {ext} for mime type: {document_meta.get('contentType')}")
                        file_name = f"{slugify(title) if title else url.split('/')[-1]}_{date_string}{ext}"
                        data_b64: str = document_meta.get("data")
                        content = base64.b64decode(data_b64)
                        await ehr_storage.upload_file(base_path, file_name, content)
                        zip_file.writestr(file_name, content)
                        logger.info(f"Downloaded and stored document: {file_name}")

                    except OneUpHealthAPIError as ex:
                        logger.error(f"Failed to download document: {url}: {ex}")
                        continue

            zip_buffer.seek(0)
            zip_size = zip_buffer.getbuffer().nbytes
            await ehr_storage.upload_file(base_path, zip_filename, zip_buffer.getvalue())

        finally:
            zip_buffer.close()

        return zip_filename, zip_size

    async def retrieve_patient_data(
        self,
        session,
        user_id: uuid.UUID,
        target_subject_id: uuid.UUID,
        applet_id: uuid.UUID,
        submit_id: uuid.UUID,
        activity_id: uuid.UUID,
        oneup_user_id: int,
        healthcare_providers: list[dict[str, str]],
    ) -> EHRMetadata | None:
        """
        Retrieve and store patient data for a subject.

        This method fetches patient data from OneUp Health and stores it using the EHR storage.

        Args:
            session: The database session to use.
            user_id (uuid.UUID): The unique identifier for the curious user.
            target_subject_id (uuid.UUID): The unique identifier for the subject.
            applet_id (uuid.UUID): The unique identifier for the applet.
            submit_id (uuid.UUID): The unique identifier for the submission.
            activity_id (uuid.UUID): The unique identifier for the activity.
            oneup_user_id (int): The OneUp Health user ID
            healthcare_providers (list[dict[str, str]]): A list of healthcare provider dictionaries.

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
        ehr_storage = await create_ehr_storage(session=session, applet_id=applet_id)
        resource_files = []
        zip_files = []
        for entry in entries:
            resource_url = entry.get("fullUrl")
            if resource_url:
                logger.info(f"Retrieving resources from {resource_url}")
                resources = await self._get_resources(f"{resource_url}/$everything?_count=100", oneup_user_id)
                if len(resources) > 0:
                    # Get the healthcare provider meta data
                    meta_source = entry.get("resource", {}).get("meta", {}).get("source")
                    healthcare_provider = next(
                        (
                            healthcare_provider
                            for healthcare_provider in healthcare_providers
                            if f"1up-external-system:{healthcare_provider['id']}" == meta_source
                        ),
                        {},
                    )

                    data = EHRData(
                        resources=resources,
                        healthcare_provider_id=healthcare_provider.get("id"),
                        healthcare_provider_name=healthcare_provider.get("name"),
                        date=datetime.now(timezone.utc),
                        submit_id=submit_id,
                        activity_id=activity_id,
                        target_subject_id=target_subject_id,
                        user_id=user_id,
                    )

                    storage_path, filename = await ehr_storage.upload_resources(data)
                    resource_files.append(f"{storage_path}/{filename}")
                    logger.info(
                        f"Stored EHR data for healthcare provider "
                        f"{healthcare_provider.get('name')} in {storage_path}/{filename}"
                    )
                    docs_zip_filename, docs_zip_size = await self._download_and_store_documents(
                        ehr_storage, oneup_user_id, data
                    )
                    if docs_zip_filename:
                        zip_files.append(
                            EHRFileMetadata(name=docs_zip_filename, size=docs_zip_size, type=EHRFileTypeEnum.DOCS)
                        )
                        logger.info(
                            f"Stored documents for healthcare provider {healthcare_provider.get('name')} "
                            f"in {docs_zip_filename} size {docs_zip_size}"
                        )

        # Upload EHR zip with all resources
        data = EHRData(
            date=datetime.now(timezone.utc),
            submit_id=submit_id,
            activity_id=activity_id,
            target_subject_id=target_subject_id,
            user_id=user_id,
        )
        ehr_zip_filename, ehr_zip_size = await ehr_storage.upload_ehr_zip(resource_files, data)
        zip_files.append(EHRFileMetadata(name=ehr_zip_filename, size=ehr_zip_size, type=EHRFileTypeEnum.EHR))

        logger.info(f"Stored EHR data in {ehr_zip_filename} size {ehr_zip_size}")

        return EHRMetadata(
            zip_files=zip_files,
            storage_path=storage_path,
        )
