"""
This module includes all the models which should be tracked by alembic

They are imported here to make sure, that they are visible to alembic
when it imports the declarative 'Base' from this module.

Import all SQLAlchemy models here
"""

import os

from config import settings
from infrastructure.database import Base  # noqa: F401, F403


def import_db_schemas():
    """This function is used in order to achieve auto imports
    of database schemas that are used by SQLAlchemy.
    """

    for app in os.listdir(settings.apps_dir):
        if app not in settings.migrations_apps:
            continue

        __import__(f"apps.{app}.db.schemas")


import_db_schemas()
