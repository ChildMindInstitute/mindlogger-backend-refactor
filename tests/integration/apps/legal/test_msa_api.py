import allure
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from pytest_mock import MockerFixture
from starlette import status

from apps.legal.router import router as legal_router
from config import settings


@allure.epic("Legal")
@allure.feature("MSA version")
class TestMsaVersionApi:
    msa_version_url = legal_router.url_path_for("msa_version_get")

    async def test_msa_version_is_public(self, app: FastAPI, mocker: MockerFixture):
        mocker.patch.object(settings.legal, "msa_version", "2026-09-15")
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test.com") as client:
            response = await client.get(self.msa_version_url)

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["result"] == {"version": "2026-09-15"}
