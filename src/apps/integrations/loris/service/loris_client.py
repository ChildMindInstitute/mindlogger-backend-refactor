import json

import aiohttp

from apps.integrations.loris.errors import LorisBadCredentialsError, LorisInvalidHostname, LorisInvalidTokenError
from apps.shared.domain.custom_validations import InvalidUrlError, validate_url


class LorisClient:
    @classmethod
    async def login_to_loris(self, hostname: str, username: str, password: str) -> str:
        try:
            hostname = validate_url(hostname)
        except InvalidUrlError as iue:
            raise LorisInvalidHostname(hostname=hostname) from iue
        timeout = aiohttp.ClientTimeout(total=60)
        loris_login_data = {
            "username": username,
            "password": password,
        }
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(
                f"{hostname}/api/v0.0.3/login",
                data=json.dumps(loris_login_data),
            ) as resp:
                if resp.status == 200:
                    response_data = await resp.json()
                    return response_data["token"]
                else:
                    error_message = await resp.text()
                    raise LorisBadCredentialsError(message=error_message)

    @classmethod
    async def list_projects(self, hostname: str, token: str):
        try:
            hostname = validate_url(hostname)
        except InvalidUrlError as iue:
            raise LorisInvalidHostname(hostname=hostname) from iue
        headers = {
            "Authorization": f"Bearer: {token}",
            "Content-Type": "application/json",
            "accept": "*/*",
        }
        timeout = aiohttp.ClientTimeout(total=60)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            url = f"{hostname}/api/v0.0.3/projects"
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
