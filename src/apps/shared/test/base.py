import json
import os

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from apps.mailing.services import TestMail
from apps.shared.test.utils import truncate_tables
from config import settings


class BaseTest:
    fixtures: list[str] = []

    @pytest.fixture(scope="class", autouse=True)
    async def initialize(self, global_session: AsyncSession):
        try:
            await self.populate_db(global_session)
            yield
        finally:
            await truncate_tables(global_session)

    @pytest.fixture(autouse=True)
    async def clear_mails(self):
        TestMail.clear_mails()

    async def populate_db(self, global_session: AsyncSession):
        for fixture in self.fixtures:
            await self.load_data(fixture, global_session)

    async def load_data(self, relative_path: str, global_session: AsyncSession):
        file = open(os.path.join(settings.apps_dir, relative_path), "r")
        data = json.load(file)
        for datum in data:
            if datum["table"] == "users":
                continue
            columns = ",".join(map(lambda field: f'"{field}"', datum["fields"].keys()))
            values = ",".join(map(_str_caster, datum["fields"].values()))
            query = text(
                f"""
            insert into "{datum['table']}"({columns}) values ({values})
            """
            )
            await global_session.execute(query)
        await global_session.commit()


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
