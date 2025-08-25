import uuid

import pytest
from pydantic import ValidationError

from apps.transfer_ownership.constants import TransferOwnershipStatus
from apps.transfer_ownership.domain import InitiateTransfer, Transfer


@pytest.mark.asyncio
class TestTransferEmailNormalization:
    async def test_transfer_model_email_normalized(self):
        model = Transfer(
            email="  MixedCase@Example.COM ",
            applet_id=uuid.uuid4(),
            key=uuid.uuid4(),
            status=TransferOwnershipStatus.PENDING,
            from_user_id=uuid.uuid4(),
        )
        assert model.email == "mixedcase@example.com"

    async def test_initiate_transfer_model_email_normalized(self):
        model = InitiateTransfer(email="  User@DOMAIN.COM ")
        assert model.email == "user@domain.com"

    async def test_transfer_model_invalid_email_raises_error(self):
        with pytest.raises(ValidationError):
            Transfer(
                email="not-an-email",
                applet_id=uuid.uuid4(),
                key=uuid.uuid4(),
                status=TransferOwnershipStatus.PENDING,
                from_user_id=uuid.uuid4(),
            )

    async def test_initiate_transfer_model_invalid_email_raises_error(self):
        with pytest.raises(ValidationError):
            InitiateTransfer(email="   not-an-email ")
