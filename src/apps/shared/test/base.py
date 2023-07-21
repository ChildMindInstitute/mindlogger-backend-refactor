import json
import os
from collections import defaultdict

import pytest
from sqlalchemy import text
from sqlalchemy.cimmutabledict import immutabledict

from apps.mailing.services import TestMail
from apps.shared.test.client import TestClient
from apps.shared.test.utils import truncate_tables, update_sequence
from config import settings
from infrastructure.database import session_manager


class BaseTest:
    chunk_size = 100
    fixtures: list[str] = []
    client = TestClient()

    @pytest.fixture(scope="class", autouse=True)
    async def initialize(self):
        await truncate_tables()
        await self.populate_db()

    @pytest.fixture(autouse=True)
    async def update_sequence(self):
        await update_sequence()

    @pytest.fixture(autouse=True)
    async def clear_mails(self):
        TestMail.clear_mails()

    async def populate_db(self):
        for fixture in self.fixtures:
            await self.load_data(fixture)

    async def load_data(self, relative_path):
        session = session_manager.get_session()
        file = open(os.path.join(settings.apps_dir, relative_path), "r")
        data = json.load(file)

        table_insertions = defaultdict(lambda: dict(columns="", values=[]))
        for datum in data:
            columns = ",".join(
                map(
                    lambda field: f'"{field}"',
                    datum["fields"].keys(),
                )
            )
            values = ",".join(map(_str_caster, datum["fields"].values()))
            table_insertions[datum["table"]]["columns"] = columns
            table_insertions[datum["table"]]["values"].append(values)
        for table, data in table_insertions.items():
            for i in range(len(data["values"]) // self.chunk_size + 1):
                start = i * self.chunk_size
                end = (i + 1) * self.chunk_size
                if len(data["values"][start:end]) == 0:
                    continue
                query = text(
                    f"""
                    insert into "{table}"({data['columns']})
                    values ({'),('.join(data['values'][start:end])})
                    """
                )
                await session.execute(
                    query,
                    execution_options=immutabledict(
                        {"synchronize_session": False}
                    ),
                )
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
