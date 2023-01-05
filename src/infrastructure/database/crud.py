from typing import Any, Generic, Type, TypeVar

from sqlalchemy import delete, func, select, update
from sqlalchemy.cimmutabledict import immutabledict
from sqlalchemy.engine import Result
from sqlalchemy.orm import Query

from apps.shared.domain import InternalModel
from infrastructure.database.base import Base
from infrastructure.database.core import session_manager

ConcreteSchema = TypeVar("ConcreteSchema", bound=Base)

__all__ = ["BaseCRUD"]


class BaseCRUD(Generic[ConcreteSchema]):
    schema_class: Type[ConcreteSchema]

    def __init__(self) -> None:
        self.session = session_manager.get_session()

    async def _execute(self, query: Query) -> Result:
        """Executes the specified query and returns the result"""
        return await self.session.execute(
            query,
            execution_options=immutabledict({"synchronize_session": "fetch"}),
        )

    async def _update(
        self,
        lookup: str,
        value: Any,
        update_schema: InternalModel | None = None,
        payload: dict[str, Any] | None = None,
    ) -> list:
        """Updates an existed instance of the model in the related table"""

        query = update(self.schema_class)
        query = query.where(getattr(self.schema_class, lookup) == value)
        if update_schema:
            query = query.values(**update_schema.dict())
        elif payload:
            query = query.values(**payload)
        else:
            return []

        query = query.returning(self.schema_class.id)

        result = await self._execute(query)
        return result.fetchall()

    async def _get(self, key: str, value: Any) -> ConcreteSchema | None:
        """Return only one result by filters"""

        query = select(self.schema_class).where(
            getattr(self.schema_class, key) == value
        )
        results = await self._execute(query=query)

        return results.scalars().one_or_none()

    async def _create(self, schema: ConcreteSchema) -> ConcreteSchema:
        """Creates a new instance of the model in the related table"""
        self.session.add(schema)
        await self.session.flush()
        await self.session.refresh(schema)
        return schema

    async def _create_many(
        self, schemas: list[ConcreteSchema]
    ) -> list[ConcreteSchema]:
        """Creates a new instance of the model in the related table"""
        self.session.add_all(schemas)
        await self.session.flush()
        for schema in schemas:
            await self.session.refresh(schema)
        return schemas

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
