import datetime as dt
import http
import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from apps.answers.domain import AppletAnswerCreate
from apps.applets.domain.applet_create_update import AppletUpdate
from apps.applets.domain.applet_full import AppletFull
from apps.applets.service.applet import AppletService
from apps.shared.test.client import TestClient
from apps.users.domain import User


@pytest.mark.asyncio
async def test_completions_version_optional_with_v2_completion(
    client: TestClient,
    session: AsyncSession,
    tom: User,
    applet: AppletFull,
    answer_create: AppletAnswerCreate,
):
    client.login(tom)
    from_date = (dt.datetime.now(dt.UTC) - dt.timedelta(days=1)).date()

    # Helper function to fetch completed activities with optional version
    async def get_activities(version: str | None):
        params = {"fromDate": from_date.isoformat()}
        if version:
            params["version"] = version
        r = await client.get(f"/answers/applet/{applet.id}/completions", params)
        assert r.status_code == http.HTTPStatus.OK, r.json()
        return r.json()["result"]["activities"]

    # Create a completion on current applet version (V1)
    v1 = applet.version
    data_v1 = answer_create.copy(deep=True)
    data_v1.created_at = dt.datetime.now(dt.UTC).replace(microsecond=0)
    resp1 = await client.post("/answers", data=data_v1)
    assert resp1.status_code == http.HTTPStatus.CREATED
    assert len(await get_activities(v1)) == 1

    # Bump applet version to V2
    srv = AppletService(session, tom.id)
    upd = AppletUpdate(**applet.dict())
    upd.display_name = (upd.display_name or "Applet") + " v2"
    v2_applet = await srv.update(applet.id, upd)
    v2 = v2_applet.version
    assert v2 != v1

    # Create a new completion on version V2
    data_v2 = answer_create.copy(deep=True)
    data_v2.version = v2
    data_v2.submit_id = uuid.uuid4()
    data_v2.created_at = dt.datetime.now(dt.UTC).replace(microsecond=0)
    resp2 = await client.post("/answers", data=data_v2)
    assert resp2.status_code == http.HTTPStatus.CREATED

    # Check completions for each version and with no version
    assert len(await get_activities(v1)) == 1
    assert len(await get_activities(v2)) == 1
    assert len(await get_activities(None)) == 2  # Both V1 and V2
