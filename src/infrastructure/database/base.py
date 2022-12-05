import os
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer
from sqlalchemy.orm import declarative_base

from config import settings
from infrastructure.database.core import engine

__all__ = ["Base", "import_models"]


def import_models():
    apps_dir = settings.apps_dir
    if not settings.apps_dir:
        return

    for app in os.listdir(apps_dir):
        if app.startswith("__"):
            continue
        if app not in settings.apps:
            continue

        try:
            __import__(f"apps.{app}.models")
        except ModuleNotFoundError as e:
            raise e


class _Base:
    """Base class for all database models."""

    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    is_deleted = Column(Boolean, default=False)


Base = declarative_base(cls=_Base, bind=engine.sync_engine)
