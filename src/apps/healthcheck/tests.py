from infrastructure.test import BaseTest


class TestHealthcheck(BaseTest):
    async def test_readiness(self):
        response = await self.client.get("readiness")
        assert response.status_code == 200
        assert response.content == b"Readiness - OK!"

    async def test_liveness(self):
        response = await self.client.get("liveness")
        assert response.status_code == 200
        assert response.content == b"Liveness - OK!"
