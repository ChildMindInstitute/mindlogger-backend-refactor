import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, MetaData
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.hybrid import hybrid_method
from sqlalchemy.orm import declarative_base

from infrastructure.database.core import engine

__all__ = ["Base"]

meta = MetaData(
    naming_convention={
        "ix": "ix_%(column_0_label)s",
        "uq": "uq_%(table_name)s_%(column_0_name)s",
        "ck": "ck_%(table_name)s_`%(constraint_name)s`",
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
        "pk": "pk_%(table_name)s",
    }
)


class _Base:
    """Base class for all database models."""

    id = Column(
        UUID(as_uuid=True), primary_key=True, default=lambda: uuid.uuid4()
    )
    created_at = Column(DateTime(), default=datetime.now)
    updated_at = Column(
        DateTime(), default=datetime.now, onupdate=datetime.now
    )
    is_deleted = Column(Boolean(), default=False)

    def __iter__(self):
        return (
            (key, val)
            for key, val in self.__dict__.items()
            if not key.startswith("_")
        )

    @hybrid_method
    def soft_exists(self, exists=True):
        if exists:
            return self.is_deleted is not True
        return self.is_deleted is True

    @soft_exists.expression  # type: ignore[no-redef]
    def soft_exists(cls, exists=True):
        if exists:
            return cls.is_deleted.isnot(True)
        return cls.is_deleted.is_(True)


Base = declarative_base(cls=_Base, bind=engine.sync_engine, metadata=meta)
