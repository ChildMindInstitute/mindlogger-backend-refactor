from config import settings
from infrastructure.utility.cdn_arbitrary import ArbitaryS3CdnClient


def get_legacy_storage():
    return ArbitaryS3CdnClient(
        region=settings.cdn.legacy_region,
        bucket=settings.cdn.legacy_bucket,
        acc_key=settings.cdn.legacy_access_key,
        sec_key=settings.cdn.legacy_secret_key,
    )
