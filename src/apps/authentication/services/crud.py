from typing import Any

from apps.authentication.db.schemas import TokenSchema
from apps.authentication.domain import TokenInDB
from apps.users.domain import UsersError
from infrastructure.database.crud import BaseCRUD

__all__ = "TokensCRUD"


class TokensCRUD(BaseCRUD[TokenSchema]):
    schema_class = TokenSchema

    async def _fetch(self, key: str, value: Any) -> TokenInDB:
        """Fetch token by email from the database."""

        # Get token from the database
        if not (instance := await self._get(key, value)):
            raise UsersError(f"No such token with {key}={value}.")

        # Get internal model
        token: TokenInDB = TokenInDB.from_orm(instance)

        return token

    async def get_by_email(self, email: str) -> TokenInDB:
        return await self._fetch(key="email", value=email)

    async def save_token(self, schema: TokenInDB) -> tuple[TokenInDB, bool]:
        """Return token instance and the created information."""

        # Save token into the database
        instance: TokenSchema = await self._create(
            TokenSchema(**schema.dict())
        )

        # Create internal data model
        token = TokenInDB.from_orm(instance)

        return token, True

    async def delete_token(self, key: str, value: str) -> bool:

        # Delete token from the database
        await self._delete(key=key, value=value)

        return True
