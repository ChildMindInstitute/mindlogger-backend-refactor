import json
import os

import pytest
from sqlalchemy import text

from config import settings
from infrastructure.database import session_manager
from .client import TestClient
from .utils import truncate_tables, update_sequence


class BaseTest:
    fixtures: list[str] = []
    client = TestClient()

    @pytest.fixture(scope="class", autouse=True)
    async def initialize(self):
        await truncate_tables()
        await self.populate_db()
        await update_sequence()

    async def populate_db(self):
        for fixture in self.fixtures:
            await self.load_data(fixture)

    async def load_data(self, relative_path):
        session = session_manager.get_session()
        file = open(os.path.join(settings.apps_dir, relative_path), "r")
        data = json.load(file)
        for datum in data:
            columns = ",".join(
                map(lambda field: f'"{field}"', datum["fields"].keys())
            )
            values = ",".join(map(_str_caster, datum["fields"].values()))
            query = text(
                f"""
            insert into "{datum['table']}"({columns}) values ({values})
            """
            )
            await session.execute(query)
        await session.commit()


def _str_caster(val):
    if val is None:
        return "null"
    if isinstance(val, str):
        return f"'{val}'"
    elif isinstance(val, (list, dict)):
        return f"'{json.dumps(val)}'"
    elif isinstance(val, bool):
        val = {True: "true", False: "false"}[val]
        return val
    return str(val)


def rollback(func):
    async def _wrap(*args, **kwargs):
        session = session_manager.get_session()
        async with session.begin():
            await func(*args, **kwargs)
            await session.rollback()
        await session.close()

    return _wrap
