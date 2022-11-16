from typing import Any, Generic, Type, TypeVar

from base import Base
from core import get_session
from sqlalchemy import func, update
from sqlalchemy.engine import Result
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Query
from sqlalchemy.sql import select
from sqlalchemy.sql.expression import delete

ConcreteSchema = TypeVar("ConcreteSchema", bound=Base)


class BaseCRUD(Generic[ConcreteSchema]):
    schema_class: ConcreteSchema

    def __init__(self, session: AsyncSession | None = None) -> None:
        self._session = session or get_session()

    async def _execute(self, query: Query) -> Result:
        """Executes the specified query and returns the result"""

        async with self._session as session:
            return await session.execute(query)

    async def _execute_commit(self, query: Query) -> Result:
        """Executes the specified query and returns the result"""

        async with self._session as session:
            data: Result = await session.execute(query)
            await session.commit()

        return data

    async def _update(
        self,
        schema_class: Type[ConcreteSchema],
        lookup: tuple[str, Any],
        payload: dict[str, Any],
    ) -> None:
        """Updates an existed instance of the model in the related table"""

        query: Query = (
            update(schema_class)
            .where(getattr(schema_class, lookup[0]) == lookup[1])
            .values(
                **payload,
            )
        )
        await self._execute_commit(query)

    async def _get(self, key: str, value: Any) -> ConcreteSchema | None:
        """Return only one result by filters"""

        query = select(self.schema_class).where(
            getattr(self.schema_class, key) == value
        )
        results = await self._execute(query=query)

        return results.scalars().one_or_none()

    async def _create(self, schema: ConcreteSchema) -> ConcreteSchema:
        """Creates a new instance of the model in the related table"""

        async with self._session as session:
            session.add(schema)
            await session.commit()
            await session.refresh(schema)

        return schema

    async def all(self) -> list[ConcreteSchema]:
        query = select(self.schema_class)
        results = await self._execute(query=query)

        return results.scalars().all()

    async def count(self) -> int:
        query = func.count(self.schema_class.id)
        results = await self._execute(query=query)

        value = results.scalar()

        if not isinstance(value, int):
            raise Exception(
                "For some reason count function returned not an integer."
                f"Value: {value}",
            )

        return value

    async def _delete(self, key: str, value: Any) -> None:
        if not (schema := await self._get(key, value)):
            return None

        query: Query = delete(self.schema_class).where(
            self.schema_class.id == schema.id
        )
        await self._execute(query)

        return None
