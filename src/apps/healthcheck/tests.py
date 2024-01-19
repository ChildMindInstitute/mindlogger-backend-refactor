from apps.shared.test import BaseTest


class TestHealthcheck(BaseTest):
    async def test_readiness(self, client):
        response = await client.get("readiness")
        assert response.status_code == 200
        assert response.content == b"Readiness - OK!"

    async def test_liveness(self, client):
        response = await client.get("liveness")
        assert response.status_code == 200
        assert response.content == b"Liveness - OK!"
