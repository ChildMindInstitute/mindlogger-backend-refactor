from apps.legal.db.schemas import LegalAcceptanceSchema
from apps.legal.domain import LegalAcceptance, LegalAcceptanceCreate
from infrastructure.database.crud import BaseCRUD


class LegalAcceptancesCRUD(BaseCRUD[LegalAcceptanceSchema]):
    schema_class = LegalAcceptanceSchema

    async def create(self, data: LegalAcceptanceCreate) -> LegalAcceptance:
        instance = await self._create(LegalAcceptanceSchema(**data.model_dump()))
        return LegalAcceptance.model_validate(instance)
