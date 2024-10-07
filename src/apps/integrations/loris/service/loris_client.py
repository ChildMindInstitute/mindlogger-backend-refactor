import json

import aiohttp
from aiohttp.client_exceptions import ClientConnectorError, ContentTypeError

from apps.integrations.loris.errors import LorisBadCredentialsError, LorisInvalidHostname, LorisInvalidTokenError
from apps.shared.domain.custom_validations import InvalidUrlError, validate_url


class LorisClient:
    @classmethod
    async def login_to_loris(self, hostname: str, username: str, password: str) -> str:
        url = LorisClient.login_url(hostname)
        try:
            hostname = validate_url(url)
        except InvalidUrlError as iue:
            raise LorisInvalidHostname(hostname=hostname) from iue
        timeout = aiohttp.ClientTimeout(total=60)
        loris_login_data = {
            "username": username,
            "password": password,
        }
        async with aiohttp.ClientSession(timeout=timeout) as session:
            try:
                async with session.post(
                    url,
                    data=json.dumps(loris_login_data),
                ) as resp:
                    if resp.status == 200:
                        try:
                            response_data = await resp.json()
                        except ContentTypeError as cce:
                            raise LorisBadCredentialsError(message=cce.message)
                        return response_data["token"]
                    else:
                        error_message = await resp.text()
                        raise LorisBadCredentialsError(message=error_message)
            except ClientConnectorError as cce:
                raise LorisBadCredentialsError(message=cce.strerror)

    @classmethod
    async def list_projects(self, hostname: str, token: str):
        url = LorisClient.projects_url(hostname)
        try:
            hostname = validate_url(url)
        except InvalidUrlError as iue:
            raise LorisInvalidHostname(hostname=hostname) from iue
        headers = {
            "Authorization": f"Bearer: {token}",
            "Content-Type": "application/json",
            "accept": "*/*",
        }
        timeout = aiohttp.ClientTimeout(total=60)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(
                url=url,
                headers=headers,
            ) as resp:
                if resp.status == 200:
                    response_data = await resp.json()
                    return response_data
                else:
                    error_message = await resp.text()
                    raise LorisInvalidTokenError(message=error_message)
                
    @classmethod
    async def get_visits_list(self, hostname: str, token: str):
        url = LorisClient.get_visits_list_url(hostname).format("loris")
        try:
            hostname = validate_url(url)
        except InvalidUrlError as iue:
            raise LorisInvalidHostname(hostname=hostname) from iue
        headers = {
            "Authorization": f"Bearer: {token}",
            "Content-Type": "application/json",
            "accept": "*/*",
        }
        timeout = aiohttp.ClientTimeout(total=60)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(
                url,
                headers=headers,
            ) as resp:
                if resp.status == 200:
                    visits_data = await resp.json()
                    return visits_data["Visits"]
                else:
                    error_message = await resp.text()
                    raise LorisInvalidTokenError(message=error_message)
                
    @classmethod
    async def get_existing_answers_from_loris(self, hostname, token, applet_id):
        url = LorisClient.ml_schema_existing_answers_url(hostname).format(applet_id)
        try:
            hostname = validate_url(url)
        except InvalidUrlError as iue:
            raise LorisInvalidHostname(hostname=hostname) from iue
        headers = {
            "Authorization": f"Bearer: {token}",
            "Content-Type": "application/json",
            "accept": "*/*",
        }
        timeout = aiohttp.ClientTimeout(total=60)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(
                url,
                headers=headers,
            ) as resp:
                if resp.status == 200:
                    response_data = await resp.json()
                    return response_data
                else:
                    error_message = await resp.text()
                    raise LorisInvalidTokenError(message=error_message)

    @classmethod
    def login_url(self, hostname: str) -> str:
        return f"https://{hostname}/api/v0.0.3/login"

    @classmethod
    def projects_url(self, hostname: str) -> str:
        return f"https://{hostname}/api/v0.0.3/projects"
    
    @classmethod
    def ml_schema_url(self, hostname: str) -> str:
        return f"https://{hostname}/mindlogger/v1/schema/"
    
    @classmethod
    def create_candidate_url(self, hostname: str) -> str:
        return f"https://{hostname}/api/v0.0.3/candidates"

    @classmethod
    def create_visit_url(self, hostname: str) -> str:
        return f"https://{hostname}/api/v0.0.3/candidates/{{}}/{{}}"

    @classmethod
    def start_visit_url(self, hostname: str) -> str:
        return f"https://{hostname}/api/v0.0.4-dev/candidates/{{}}/{{}}"
    
    @classmethod
    def add_instruments_url(self, hostname: str) -> str:
        return f"https://{hostname}/api/v0.0.4-dev/candidates/{{}}/{{}}/instruments"

    @classmethod
    def instrument_data_url(self, hostname: str) -> str:
        return f"https://{hostname}/api/v0.0.3/candidates/{{}}/{{}}/instruments/{{}}"
    
    @classmethod
    def ml_schema_existing_versions_url(self, hostname: str) -> str:
        return f"https://{hostname}/mindlogger/v1/applet/{{}}/versions"
    
    @classmethod
    def ml_schema_existing_answers_url(self, hostname: str) -> str:
        return f"https://{hostname}/mindlogger/v1/applet/{{}}/answers"
    
    @classmethod
    def get_visits_list_url(self, hostname: str) -> str:
        return f"https://{hostname}/api/v0.0.3/projects/{{}}/visits"

    @classmethod
    def ml_visits_for_applet_url(self, hostname: str) -> str:
        return f"https://{hostname}/mindlogger/v1/applet/{{}}/visits"
