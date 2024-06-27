import uuid

import pytest

from apps.integrations.loris.router import router as loris_router
from apps.shared.test.client import TestClient
from apps.users.domain import User


@pytest.mark.usefixtures("user")
class TestLorisRouter:
    start_transmit_process_url = loris_router.url_path_for("start_transmit_process")
    consent_create_url = loris_router.url_path_for("consent_create")
    # consent_get_by_id_url = loris_router.url_path_for("consent_get_by_id")
    # consent_get_by_user_id_url = loris_router.url_path_for("consent_get_by_user_id")
    # consent_update_url = loris_router.url_path_for("consent_update")

    async def test_start_transmit_process(self, client: TestClient, user: User, uuid_zero: uuid.UUID):
        applet_data = {"applet_id": str(uuid_zero)}
        _data = {
            "user_id": uuid_zero,
            "activities": [{"activity_id": uuid_zero, "answer_id": uuid_zero, "version": "0.1.2", "visit": "test"}],
        }
        client.login(user)
        response = await client.post(self.start_transmit_process_url, data=[_data], query=applet_data)
        assert response.status_code == 202

    # async def test_consent_create(self, client: TestClient, user: User, uuid_zero: uuid.UUID):
    #     payload = {
    #         "userId": str(uuid_zero),
    #         "isReadyShareData": True,
    #         "isReadyShareMediaData": True
    #     }
    #     client.login(user)
    #     response = await client.post(self.consent_create_url, data=payload)
    #     assert response.status_code == 201

    # async def test_consent_get_by_id(self, client: TestClient, user: User, uuid_zero: uuid.UUID):
    #     # create consent
    #     consent_id = str(uuid_zero)
    #     client.login(user)
    #     response = await client.get(f"/integrations/loris/consent/{consent_id}/")
    #     assert response.status_code == 200

    # async def test_consent_get_by_user_id(self, client: TestClient, user: User, uuid_zero: uuid.UUID):
    #     # create consent
    #     user_id = str(uuid_zero)
    #     client.login(user)
    #     response = await client.get(f"/integrations/loris/consent/users/{user_id}/")
    #     assert response.status_code == 200

    # async def test_consent_update(self, client: TestClient, user: User, uuid_zero: uuid.UUID):
    #     # create consent
    #     consent_id = str(uuid_zero)
    #     client.login(user)
    #     payload = {
    #         "userId": str(uuid_zero),
    #         "isReadyShareData": False,
    #         "isReadyShareMediaData": True
    #     }
    #     response = await client.put(f"/integrations/loris/consent/{consent_id}/", data=payload)
    #     assert response.status_code == 200
