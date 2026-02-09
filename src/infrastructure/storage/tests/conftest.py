import os

import boto3
import pytest
from moto import mock_aws

from infrastructure.storage.tests import ANSWER_BUCKET_NAME


@pytest.fixture(scope="function")
async def aws_credentials():
    """Mocked AWS Credentials for moto."""
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["AWS_DEFAULT_REGION"] = "us-east-1"


@pytest.fixture(scope="function")
async def s3_client(aws_credentials):
    """
    Return a mocked S3 client
    """
    with mock_aws():
        yield boto3.client("s3", region_name="us-east-1")


# @pytest.fixture(scope="function")
# async def mocked_aws(aws_credentials):
#     """
#     Mock all AWS interactions
#     Requires you to create your own boto3 clients
#     """
#     with mock_aws():
#         yield


@pytest.fixture(scope="function")
def s3_resource():
    with mock_aws():
        s3 = boto3.resource("s3", region_name="us-east-1")
        yield s3


@pytest.fixture(scope="function")
def answer_bucket(s3_resource):
    """Create the bucket in Moto"""
    bucket = s3_resource.create_bucket(Bucket=ANSWER_BUCKET_NAME)
    bucket.create()
    yield bucket
