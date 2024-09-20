import json

import aiohttp
from aiohttp.client_exceptions import ClientConnectorError, ContentTypeError

from apps.integrations.loris.errors import LorisBadCredentialsError, LorisInvalidHostname, LorisInvalidTokenError
from apps.shared.domain.custom_validations import InvalidUrlError, validate_url


class LorisClient:
    @classmethod
    async def login_to_loris(self, hostname: str, username: str, password: str) -> str:
        url = f"https://{hostname}/api/v0.0.3/login"
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
        url = f"https://{hostname}/api/v0.0.3/projects"
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
