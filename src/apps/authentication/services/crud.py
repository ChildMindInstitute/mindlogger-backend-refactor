from typing import Any

from apps.authentication.db.schemas import TokenSchema
from apps.authentication.domain import Token, TokenCreate
from apps.authentication.services.security import AuthenticationService
from apps.users.domain import UsersError
from infrastructure.database.crud import BaseCRUD

__all__ = ["TokensCRUD"]


class TokensCRUD(BaseCRUD[TokenSchema]):
    schema_class = TokenSchema

    async def _fetch(self, key: str, value: Any) -> Token:
        """Fetch token by email from the database."""

        # Get token from the database
        if not (instance := await self._get(key, value)):
            raise UsersError(f"No such token with {key}={value}.")

        # Get internal model
        token: Token = Token.from_orm(instance)

        return token

    async def get_by_email(self, email: str) -> Token:
        return await self._fetch(key="email", value=email)

    async def save(self, schema: TokenCreate) -> tuple[Token, bool]:
        """Return token instance and the created information."""

        # Save token into the database
        instance: TokenSchema = await self._create(
            TokenSchema(**schema.dict())
        )

        # Create internal data model
        token: Token = Token.from_orm(instance)

        return token, True

    async def delete(self, id_: int):
        await self._delete(key="id", value=id_)

    async def refresh_access_token(self, id_: int) -> Token:
        instance: Token = await self._fetch(key="id", value=id_)
        access_token = AuthenticationService.create_access_token(
            data={"sub": instance.email}
        )
        await self._update(
            lookup=("id", id_), payload={"access_token": access_token}
        )
        instance: Token = await self._fetch(key="id", value=id_)
        return instance
