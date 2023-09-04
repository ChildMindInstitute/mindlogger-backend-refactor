from config import settings
from infrastructure.utility.cdn_arbitrary import CdnClientS3


def get_legacy_storage():
    return CdnClientS3(
        region=settings.cdn.legacy_region,
        bucket=settings.cdn.legacy_bucket,
        acc_key=settings.cdn.legacy_access_key,
        sec_key=settings.cdn.legacy_secret_key,
    )
