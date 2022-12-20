from typing import Any, Generic, Type, TypeVar

from sqlalchemy import delete, func, select, update
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
        return await self.session.execute(query)

    async def _execute_commit(self, query: Query) -> Result:
        """Executes the specified query and returns the result"""

        result: Result = await self._execute(query)
        await self.session.commit()

        return result

    async def _update(
        self, lookup: str, value: Any, update_schema: InternalModel
    ) -> ConcreteSchema:
        """Updates an existed instance of the model in the related table"""

        query: Query = (
            update(self.schema_class)
            .where(getattr(self.schema_class, lookup) == value)
            .values(**update_schema.dict())
            .returning(self.schema_class.id)
        )
        result: Result = await self._execute_commit(query)
        instance_id: int = result.scalar_one()

        if not (
            instance_schema := await self._get(key="id", value=instance_id)
        ):
            raise Exception("Can not fetch the updated instance.")

        return instance_schema

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
        await self.session.commit()

        return schema

    async def _all(self) -> list[ConcreteSchema]:
        query: Query = select(self.schema_class)
        results: Result = await self._execute(query=query)

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
