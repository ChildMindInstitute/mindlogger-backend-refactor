from uuid import uuid4

from apps.workspaces.domain.workspace import WorkspaceArbitrary
from infrastructure.storage.storage import create_answer_client
from infrastructure.storage.storage_arbitrary import ArbitraryS3StorageClient


class TestArbitraryStorageClients:

    def test_create_answer_client_arbitrary(self):
        """Test a non-arbitrary server client with a different AWS region"""
        db_uri = "sqlite:///:memory:"
        storage_url = "https://s3.eu-central-2.amazonaws.com"
        storage_region = "eu-central-2"
        bucket = "test-bucket"
        info = WorkspaceArbitrary(
            database_uri=db_uri,
            storage_url=storage_url,
            storage_region=storage_region,
            use_arbitrary=True,
            storage_type="s3",
            storage_bucket=bucket,
            storage_access_key="AAAAA",
            storage_secret_key="BBBBB",
            user_id=uuid4(),
            id=uuid4(),
        )

        client = create_answer_client(info)

        # Make sure it's the arbitrary sub type
        assert isinstance(client, ArbitraryS3StorageClient)

        assert client.config.bucket == bucket
        assert client.config.endpoint_url == storage_url
        assert client.config.region == storage_region

        presign = client.generate_presigned_post("asdf.jpg")
        assert storage_region in presign["url"]

    def test_create_answer_client_arbitrary_dr(self, cdn_override_settings):
        """Test a arbitrary server client with DR settings (should do nothing)"""
        db_uri = "sqlite:///:memory:"
        storage_url = "https://s3.eu-central-2.amazonaws.com"
        storage_region = "eu-central-2"
        bucket = "test-bucket"
        info = WorkspaceArbitrary(
            database_uri=db_uri,
            storage_url=storage_url,
            storage_region=storage_region,
            use_arbitrary=True,
            storage_type="s3",
            storage_bucket=bucket,
            storage_access_key="AAAAA",
            storage_secret_key="BBBBB",
            user_id=uuid4(),
            id=uuid4(),
        )

        client = create_answer_client(info, cdn_override_settings)

        # Make sure it's the arbitrary sub type
        assert isinstance(client, ArbitraryS3StorageClient)

        assert client.config.bucket == bucket
        assert client.config.endpoint_url == storage_url
        assert client.config.region == storage_region

        presign = client.generate_presigned_post("asdf.jpg")
        assert storage_region in presign["url"]