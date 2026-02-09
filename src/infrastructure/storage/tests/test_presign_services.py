import os
import uuid

import boto3
import pytest
from moto import mock_aws
from sqlalchemy.ext.asyncio import AsyncSession

from apps.applets.domain.applet_full import AppletFull
from apps.users import User
from apps.workspaces.db.schemas import UserAppletAccessSchema
from apps.workspaces.domain.constants import Role
from infrastructure.storage.cdn_client import CDNClient
from infrastructure.storage.cdn_config import CdnConfig
from infrastructure.storage.presign_services import S3PresignService

ANSWER_BUCKET_NAME = "test-answer-bucket"


class TestS3PresignService:
    """Test for the S3PresignService"""

    @pytest.fixture(scope="function")
    async def aws_credentials(self):
        """Mocked AWS Credentials for moto."""
        os.environ["AWS_ACCESS_KEY_ID"] = "testing"
        os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
        os.environ["AWS_SECURITY_TOKEN"] = "testing"
        os.environ["AWS_SESSION_TOKEN"] = "testing"
        os.environ["AWS_DEFAULT_REGION"] = "us-east-1"

    @pytest.fixture(scope="function")
    async def s3(self, aws_credentials):
        """
        Return a mocked S3 client
        """
        with mock_aws():
            yield boto3.client("s3", region_name="us-east-1")

    @pytest.fixture(scope="function")
    async def mocked_aws(self, aws_credentials):
        """
        Mock all AWS interactions
        Requires you to create your own boto3 clients
        """
        with mock_aws():
            yield

    @pytest.fixture
    def answer_bucket(self, s3):
        """Create the bucket in Moto"""
        s3.create_bucket(Bucket=ANSWER_BUCKET_NAME)

    @pytest.fixture
    async def answer_storage_client(self, s3) -> CDNClient:
        config = CdnConfig(
            endpoint_url=None,
            region="us-east-1",
            bucket=ANSWER_BUCKET_NAME,
        )
        return CDNClient(config, env="test")

    @pytest.fixture
    async def s3_presign_service(self, session: AsyncSession, tom: User, applet_one: AppletFull, answer_storage_client):
        access = UserAppletAccessSchema()
        access.applet_id = applet_one.id
        access.user_id = tom.id
        access.role = Role.MANAGER

        return S3PresignService(session, tom.id, applet_one.id, access, answer_storage_client)

    @pytest.fixture
    async def s3_presign_service_respondent(
        self, session: AsyncSession, bob: User, applet_one: AppletFull, answer_storage_client
    ):
        """Make the user a RESPONDENT on the applet"""
        access = UserAppletAccessSchema()
        access.applet_id = applet_one.id
        access.user_id = bob.id
        access.role = Role.RESPONDENT

        return S3PresignService(session, bob.id, applet_one.id, access, answer_storage_client)

    async def test_presign_service(self, tom: User, applet_one: AppletFull, s3_presign_service: S3PresignService):
        """Happy path"""
        url = f"s3://{ANSWER_BUCKET_NAME}/mindlogger/answer/{tom.id}/{applet_one.id}/file.jpg"

        signed = await s3_presign_service.presign([url])

        assert len(signed) == 1
        assert signed[0] is not None
        assert ANSWER_BUCKET_NAME in signed[0]

    async def test_presign_service_legacy_url(
        self, tom: User, applet_one: AppletFull, s3_presign_service: S3PresignService
    ):
        """Happy path"""
        url = f"s3://{ANSWER_BUCKET_NAME}/mindlogger/answer/{tom.id}/{applet_one.id}/file.jpg"

        signed = await s3_presign_service.presign([url])

        assert len(signed) == 1
        assert signed[0] is not None
        assert ANSWER_BUCKET_NAME in signed[0]

    async def test_presign_service_wrong_applet(
        self, tom: User, applet_one: AppletFull, s3_presign_service: S3PresignService
    ):
        """Applet ID does not match"""
        url = f"s3://{ANSWER_BUCKET_NAME}/mindlogger/answer/{tom.id}/{uuid.uuid4()}/file.jpg"

        signed = await s3_presign_service.presign([url])

        assert len(signed) == 1
        assert signed[0] is not None
        assert url == signed[0]

    async def test_presign_service_invalid_url(
        self, tom: User, applet_one: AppletFull, s3_presign_service: S3PresignService
    ):
        """A URL that does not match current or legacy"""
        url = f"s3://{ANSWER_BUCKET_NAME}/not/valid/path/file.jpg"

        signed = await s3_presign_service.presign([url])
        assert len(signed) == 1
        assert signed[0] is not None
        assert url == signed[0]

    async def test_presign_service_respondent(
        self, bob: User, applet_one: AppletFull, s3_presign_service_respondent: S3PresignService
    ):
        """The user is a respodent and does not have access"""
        url = f"s3://{ANSWER_BUCKET_NAME}/mindlogger/answer/{bob.id}/{applet_one.id}/file.jpg"

        signed = await s3_presign_service_respondent.presign([url])

        assert len(signed) == 1
        assert signed[0] is not None
        assert url == signed[0]
