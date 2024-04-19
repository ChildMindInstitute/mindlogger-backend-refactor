import uuid

from sqlalchemy import Boolean, Column, DateTime, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.hybrid import hybrid_method
from sqlalchemy.orm import declarative_mixin

__all__ = ("SoftDeletable", "HistoryAware", "MigratedMixin")


class SoftDeletable:
    is_deleted = Column(Boolean(), default=False)

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


class HistoryAware:
    @classmethod
    def generate_id_version(cls, id_: str | uuid.UUID, version: str) -> str:
        return f"{id_}_{version}"

    @classmethod
    def split_id_version(cls, id_version: str) -> tuple[uuid.UUID, str]:
        parts = id_version.split("_")
        if len(parts) != 2:
            raise Exception(f"Wrong id_version format: {id_version}")

        return uuid.UUID(parts[0]), parts[1]

    @hybrid_method
    def id_from_history_id(self, field):
        if field:
            return self.split_id_version(field)[0]
        return None

    @id_from_history_id.expression  # type: ignore[no-redef]
    def id_from_history_id(self, field):
        return func.split_part(field, text("'_'"), text("1")).cast(UUID)

    @hybrid_method
    def version_from_history_id(self, field):
        if field:
            return self.split_id_version(field)[1]
        return None

    @version_from_history_id.expression  # type: ignore[no-redef]
    def version_from_history_id(self, field):
        return func.split_part(field, text("'_'"), text("2"))


@declarative_mixin
class MigratedMixin:
    migrated_date = Column(DateTime(), default=None, server_default=None, nullable=True)
