import asyncio
import datetime
import uuid
from functools import wraps

import typer
from rich import print

from apps.authentication.domain.token import JWTClaim
from apps.authentication.services import AuthenticationService

app = typer.Typer()


def coro(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        return asyncio.run(f(*args, **kwargs))

    return wrapper


@app.command(short_help="Generate access token")
@coro
async def generate(
    user_id: uuid.UUID = typer.Argument(help="User Id"),
    ttl: int = typer.Option(None, "--ttl", help="ttl in seconds"),
):
    payload: dict = {JWTClaim.sub: str(user_id)}

    if ttl:
        expires_delta = datetime.timedelta(seconds=ttl)
        expire = datetime.datetime.utcnow() + expires_delta
        payload[JWTClaim.exp] = expire

    access_token = AuthenticationService.create_access_token(payload)
    print(access_token)
