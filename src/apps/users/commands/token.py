import datetime
import uuid

import typer
from rich import print

from apps.authentication.domain.token import JWTClaim
from apps.authentication.services import AuthenticationService
from infrastructure.commands.utils import coro

app = typer.Typer()


@app.command(short_help="Generate access token")
@coro
async def generate(
    user_id: uuid.UUID = typer.Argument(help="User Id"),
    ttl: int = typer.Option(None, "--ttl", help="ttl in seconds"),
):
    payload: dict = {JWTClaim.sub: str(user_id)}

    if ttl:
        expires_delta = datetime.timedelta(seconds=ttl)
        expire = datetime.datetime.now(datetime.UTC).replace(tzinfo=None) + expires_delta
        payload[JWTClaim.exp] = expire

    access_token = AuthenticationService.create_access_token(payload)
    print(access_token)
