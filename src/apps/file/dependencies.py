from config import CDNSettings, settings
from infrastructure.utility import CDNClient

# TODO Pycharm says this is not used
def get_legacy_storage():
    settings_cdn = CDNSettings(
        region=settings.cdn.legacy_region,
        bucket=settings.cdn.legacy_bucket,
        access_key=settings.cdn.legacy_access_key,
        secret_key=settings.cdn.legacy_secret_key,
        ttl_signed_urls=settings.cdn.ttl_signed_urls,
    )
    return CDNClient(settings_cdn, env=settings.env)
