from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer
from sqlalchemy.orm import declarative_base

from infrastructure.database.core import engine

__all__ = ["Base"]


class _Base:
    """Base class for all database models."""

    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    is_deleted = Column(Boolean, default=False)

    @classmethod
    def sequence_name(cls):
        return f"{cls.__tablename__}_id_seq"


Base = declarative_base(cls=_Base, bind=engine.sync_engine)
