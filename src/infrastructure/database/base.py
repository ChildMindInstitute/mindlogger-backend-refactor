import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, MetaData, TypeDecorator, inspect, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base

__all__ = ["Base", "UTCDateTime"]

from infrastructure.database.mixins import SoftDeletable

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


class UTCDateTime(TypeDecorator):
    impl = DateTime

    def process_result_value(self, value, dialect):
        if value is not None:
            if value.tzinfo is None:
                # Assume value is UTC if tzinfo is None
                value = value.replace(tzinfo=timezone.utc)
        return value


class Base(SoftDeletable, _Base):  # type: ignore
    """Base class for all database models."""

    __abstract__ = True

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=lambda: uuid.uuid4(),
        server_default=text("gen_random_uuid()"),
    )
    created_at = Column(
        UTCDateTime(),
        default=datetime.utcnow,
        server_default=text("timezone('utc', now())"),
    )
    updated_at = Column(
        UTCDateTime(),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        server_default=text("timezone('utc', now())"),
        server_onupdate=text("timezone('utc', now())"),
    )
    migrated_date = Column(
        UTCDateTime(),
        default=None,
        server_default=None,
        nullable=True,
    )
    migrated_updated = Column(
        UTCDateTime(),
        default=None,
        server_default=None,
        nullable=True,
    )

    def __iter__(self):
        info = inspect(self)
        return ((c.key, getattr(self, c.key)) for c in info.mapper.column_attrs if c.key not in info.unloaded)
