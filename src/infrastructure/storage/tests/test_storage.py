from sqlalchemy.ext.asyncio.session import AsyncSession

from apps.users import User
from config import Settings, settings
from infrastructure.storage.storage import (
    create_answer_client,
    get_log_storage,
    get_media_storage,
    get_operations_storage,
    select_answer_storage,
)
from infrastructure.storage.tests import ANSWER_OVERRIDE, MEDIA_OVERRIDE, OPERATIONS_OVERRIDE


class TestStorageClients:
    """Basic tests for fetching/building storage clients"""

    def test_create_answer_client(self, normal_storage_settings: Settings) -> None:
        """Test a non-arbitrary server client"""
        client = create_answer_client(app_settings=normal_storage_settings)

        assert client.config.bucket == normal_storage_settings.cdn.bucket_answer

        presign = client.generate_presigned_post("asdf.jpg")
        assert presign is not None
        assert normal_storage_settings.cdn.bucket_answer in presign["url"]

    async def test_select_answer_storage_client(
        self, tom: User, session: AsyncSession, normal_storage_settings: Settings
    ) -> None:
        """Test a non-arbitrary server client"""
        client = await select_answer_storage(owner_id=tom.id, session=session, app_settings=normal_storage_settings)
        assert client.config.bucket == normal_storage_settings.cdn.bucket_answer
        assert client.config.bucket_override is None

    async def test_select_answer_storage_client_dr(
        self, tom: User, session: AsyncSession, cdn_override_settings
    ) -> None:
        """Test a non-arbitrary server client"""
        client = await select_answer_storage(owner_id=tom.id, session=session, app_settings=cdn_override_settings)
        assert client.config.bucket == cdn_override_settings.cdn.bucket_answer
        assert client.config.bucket_override == ANSWER_OVERRIDE

    async def test_get_media_storage_client(self, normal_storage_settings: Settings) -> None:
        """Test a non-arbitrary server client"""
        client = await get_media_storage(normal_storage_settings)
        assert client.config.bucket == normal_storage_settings.cdn.bucket
        assert client.config.bucket_override is None

        presign = client.generate_presigned_post("asdf.jpg")
        assert presign is not None
        assert normal_storage_settings.cdn.bucket in presign["url"]

    async def test_get_media_storage_client_dr(self, cdn_override_settings) -> None:
        """Test a non-arbitrary server client with DR settings"""

        client = await get_media_storage(cdn_override_settings)
        assert client.config.bucket == cdn_override_settings.cdn.bucket
        assert client.config.bucket_override == MEDIA_OVERRIDE

        presign = client.generate_presigned_post("asdf.jpg")
        assert presign is not None
        # This might not be useful
        assert client.config.endpoint_url in presign["url"]

    async def test_get_operations_storage_client(self, normal_storage_settings: Settings) -> None:
        """Test a non-arbitrary server client"""
        client = await get_operations_storage(normal_storage_settings)
        assert client.config.bucket == normal_storage_settings.cdn.bucket_operations
        assert client.config.bucket_override is None

        presign = client.generate_presigned_post("asdf.jpg")
        assert presign is not None
        assert normal_storage_settings.cdn.bucket_operations in presign["url"]

    async def test_get_operations_storage_client_dr(self, cdn_override_settings) -> None:
        """Test a non-arbitrary server client"""
        client = await get_operations_storage(cdn_override_settings)
        assert client.config.bucket == cdn_override_settings.cdn.bucket_operations
        assert client.config.bucket_override == OPERATIONS_OVERRIDE

        presign = client.generate_presigned_post("asdf.jpg")
        assert presign is not None
        assert OPERATIONS_OVERRIDE in presign["url"]

    async def test_get_logs_storage_client(self, normal_storage_settings: Settings) -> None:
        """Test a non-arbitrary server client"""
        client = await get_log_storage(normal_storage_settings)
        assert client.config.bucket == normal_storage_settings.cdn.bucket_answer
        assert client.config.bucket_override is None

        presign = client.generate_presigned_post("asdf.jpg")
        assert presign is not None

    async def test_get_logs_storage_client_dr(self, cdn_override_settings) -> None:
        """Test a non-arbitrary server client"""
        client = await get_log_storage(cdn_override_settings)
        assert client.config.bucket == cdn_override_settings.cdn.bucket_answer
        assert client.config.bucket_override == ANSWER_OVERRIDE

        presign = client.generate_presigned_post("asdf.jpg")
        assert presign is not None
        # This might not be useful
        assert client.config.endpoint_url in presign["url"]


class TestLocalStorageSettings:
    """Tests for when local storage type setting are enabled, mostly for local development"""

    async def test_get_media_storage_client(self, local_storage_settings: Settings) -> None:
        """Test a non-arbitrary server client"""
        client = await get_media_storage(local_storage_settings)
        assert client.config.bucket == local_storage_settings.cdn.bucket
        assert client.config.bucket_override is None

        presign = client.generate_presigned_post("asdf.jpg")
        assert presign is not None
        assert local_storage_settings.cdn.bucket in presign["url"]
        assert local_storage_settings.cdn.storage_address in presign["url"]
