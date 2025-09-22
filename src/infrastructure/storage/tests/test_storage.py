from uuid import uuid4

from apps.workspaces.domain.workspace import WorkspaceArbitrary
from config import settings
from infrastructure.storage.cdn_arbitrary import ArbitraryS3CdnClient
from infrastructure.storage.storage import create_answer_client


def test_create_answer_client() -> None:
    """Test a non arbitrary server client"""
    client = create_answer_client(None)

    assert client.config.bucket == settings.cdn.bucket_answer
    assert client.config.bucket == "answer"

    presign = client.generate_presigned_post("asdf.jpg")
    assert presign is not None
    assert client.config.endpoint_url in presign["url"]


def test_create_answer_client_arbitrary():
    """Test a non arbitrary server client with a different AWS region"""
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
    assert isinstance(client, ArbitraryS3CdnClient)

    assert client.config.bucket == bucket
    assert client.config.endpoint_url == storage_url
    assert client.config.region == storage_region

    presign = client.generate_presigned_post("asdf.jpg")
    assert storage_region in presign["url"]
