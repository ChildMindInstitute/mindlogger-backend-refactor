import uuid

from apps.legal.constants import LegalDocType
from apps.legal.db.schemas import LegalAcceptanceSchema
from apps.legal.domain import LegalAcceptance, LegalAcceptanceCreate
from infrastructure.database.crud import BaseCRUD


class LegalAcceptancesCRUD(BaseCRUD[LegalAcceptanceSchema]):
    schema_class = LegalAcceptanceSchema

    async def create(self, data: LegalAcceptanceCreate) -> LegalAcceptance:
        instance = await self._create(LegalAcceptanceSchema(**data.model_dump()))
        return LegalAcceptance.model_validate(instance)

    async def has_accepted(self, user_id: uuid.UUID, doc_type: LegalDocType, version: str | None = None) -> bool:
        """Whether the user accepted this version of the document, or any version if none is given."""
        filters = {"user_id": user_id, "doc_type": doc_type}
        if version is not None:
            filters["version"] = version
        return await self.count(**filters) > 0
