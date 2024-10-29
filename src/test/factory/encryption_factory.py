import uuid

from apps.applets.domain.base import Encryption
from apps.applets.tests import constants


def build_encryption() -> Encryption:
    return Encryption(
        public_key=str(constants.TEST_PUBLIC_KEY),
        prime=str(constants.TEST_PRIME),
        base=str(constants.TEST_BASE),
        # Account id is not used co can be random uuid
        account_id=str(uuid.uuid4()),
    )
