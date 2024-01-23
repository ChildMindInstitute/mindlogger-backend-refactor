import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, MetaData, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.hybrid import hybrid_method
from sqlalchemy.orm import declarative_base, declarative_mixin

__all__ = ["Base", "MigratedMixin"]

meta = MetaData(
    naming_convention={
        "ix": "ix_%(column_0_label)s",
        "uq": "uq_%(table_name)s_%(column_0_name)s",
        "ck": "ck_%(table_name)s_`%(constraint_name)s`",
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
        "pk": "pk_%(table_name)s",
    }
)


_Base = declarative_base(metadata=meta)


class Base(_Base):  # type: ignore
    """Base class for all database models."""

    __abstract__ = True

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=lambda: uuid.uuid4(),
        server_default=text("gen_random_uuid()"),
    )
    created_at = Column(
        DateTime(),
        default=datetime.utcnow,
        server_default=text("timezone('utc', now())"),
    )
    updated_at = Column(
        DateTime(),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        server_default=text("timezone('utc', now())"),
        server_onupdate=text("timezone('utc', now())"),
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


@declarative_mixin
class MigratedMixin:

    migrated_date = Column(
        DateTime(),
        default=None,
        server_default=None,
        nullable=True,
    )
    migrated_updated = Column(
        DateTime(),
        default=None,
        server_default=None,
        nullable=True,
    )
