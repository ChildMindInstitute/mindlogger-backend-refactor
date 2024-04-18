import datetime
import uuid

from pydantic import BaseModel, Extra

from apps.activities.domain.conditional_logic import ConditionalLogic

__all__ = [
    "UnencryptedApplet",
    "Consent",
    "ConsentUpdate",
    "ConsentCreate",
    "PublicConsent",
    "ConsentRequest",
    "ConsentUpdateRequest",
]


class Item(BaseModel):
    id: uuid.UUID
    question: str
    responseType: str
    responseValues: dict | None
    config: dict | None
    name: str
    isHidden: bool | None
    conditionalLogic: ConditionalLogic | None
    allowEdit: bool | None


# todo write own BaseActivityItem
# use for config - SingleSelectionConfig
# use for responseValues - class SingleSelectionValues(PublicModel):
# class ActivityItem(PublicModel):
class Activitie(BaseModel):
    id: uuid.UUID
    name: str
    description: str
    splash_screen: str = ""
    image: str = ""
    order: int
    createdAt: datetime.datetime
    # items: list[BaseActivityItem]
    items: list[Item]


class UnencryptedApplet(BaseModel):
    id: uuid.UUID
    displayName: str
    description: str
    # about: str
    # image: str = ""
    # watermark: str = ""
    # version: str
    # createdAt: datetime.datetime
    # respondent_nickname: str
    activities: list[Activitie]


class LorisServerResponse(BaseModel):
    pass


def to_camelcase(payload: str) -> str:
    if "_" not in payload:
        return payload

    return "".join(
        word.capitalize() if index else word
        for index, word in enumerate(payload.split("_"))
    )


class InternalModel(BaseModel):
    class Config:
        arbitrary_types_allowed = True
        extra = Extra.forbid
        orm_mode = True
        use_enum_values = True
        allow_population_by_field_name = True
        validate_assignment = True
        alias_generator = to_camelcase


class ConsentCreate(InternalModel):
    user_id: uuid.UUID
    is_ready_share_data: bool
    is_ready_share_media_data: bool


class ConsentUpdate(ConsentCreate):
    pass


class Consent(ConsentCreate, InternalModel):
    id: uuid.UUID


class PublicConsent(ConsentCreate):
    pass


class ConsentRequest(ConsentCreate):
    pass


class ConsentUpdateRequest(ConsentUpdate):
    pass
