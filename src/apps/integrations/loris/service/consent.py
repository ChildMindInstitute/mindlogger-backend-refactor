import uuid

from apps.integrations.loris.crud.consent import ConsentCRUD
from apps.integrations.loris.domain.domain import (
    Consent,
    ConsentCreate,
    ConsentRequest,
    ConsentUpdate,
    ConsentUpdateRequest,
    PublicConsent,
)

__all__ = ["ConsentService"]


class ConsentService:
    def __init__(self, session):
        self.session = session

    async def create_consent(self, new_consent: ConsentRequest) -> PublicConsent:
        # Create consent
        consent: Consent = await ConsentCRUD(self.session).save(
            ConsentCreate(
                user_id=new_consent.user_id,
                is_ready_share_data=new_consent.is_ready_share_data,
                is_ready_share_media_data=new_consent.is_ready_share_media_data,  # noqa: E501
            )
        )

        return PublicConsent(**consent.dict())

    async def get_consent_by_id(self, consent_id: uuid.UUID) -> PublicConsent:
        consent: Consent = await ConsentCRUD(self.session).get_by_id(pk=consent_id)

        return PublicConsent(**consent.dict())

    async def get_consent_by_user_id(self, user_id: uuid.UUID) -> PublicConsent:
        consent: Consent = await ConsentCRUD(self.session).get_by_user_id(user_id=user_id)

        return PublicConsent(**consent.dict())

    async def update_consent(
        self,
        consent_id: uuid.UUID,
        new_consent: ConsentUpdateRequest,
    ) -> PublicConsent:
        # Update consent
        consent: Consent = await ConsentCRUD(self.session).update(
            pk=consent_id,
            schema=ConsentUpdate(
                user_id=new_consent.user_id,
                is_ready_share_data=new_consent.is_ready_share_data,
                is_ready_share_media_data=new_consent.is_ready_share_media_data,  # noqa: E501
            ),
        )

        return PublicConsent(**consent.dict())
