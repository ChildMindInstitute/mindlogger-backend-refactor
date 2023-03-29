import uuid

from pydantic import BaseModel, Field, root_validator, validator

from apps.activities.domain.response_type_config import (
    ResponseType,
    NoneResponseType,
    ResponseTypeConfig,
    ResponseTypeValueConfig,
    TextConfig,
)
from apps.activities.domain.response_values import ResponseValueConfig
from apps.shared.domain import InternalModel, PublicModel


class BaseActivityItem(BaseModel):
    question: dict[str, str] = Field(default_factory=dict)
    response_type: ResponseType
    response_values: ResponseValueConfig | None
    config: ResponseTypeConfig = Field(default_factory=TextConfig)
    name: str

    @validator("name", allow_reuse=True)
    def validate_name(cls, value):
        # name must contain only alphanumeric symbols or underscore
        if not value.replace("_", "").isalnum():
            raise ValueError(
                "Name must contain only alphanumeric symbols or underscore"
            )
        return value

    @root_validator(allow_reuse=True)
    def validate_response_type(cls, values):
        response_type = values.get("response_type")
        response_values = values.get("response_values")
        config = values.get("config")
        if response_type in ResponseTypeValueConfig:
            if response_type not in list(NoneResponseType):
                if not isinstance(
                    response_values,
                    type(ResponseTypeValueConfig[response_type]["value"]),
                ):
                    raise ValueError(
                        f"response_values must be of type {ResponseTypeValueConfig[response_type]['value']}"
                    )
            else:
                if response_values is not None:
                    raise ValueError(
                        f"response_values must be of type {ResponseTypeValueConfig[response_type]['value']}"
                    )

            if not isinstance(
                config, ResponseTypeValueConfig[response_type]["config"]
            ):
                raise ValueError(
                    f"config must be of type {ResponseTypeValueConfig[response_type]['config']}"
                )
            print("hello")

        else:
            raise ValueError(f"response_type must be of type {ResponseType}")
        return values


class ActivityItem(BaseActivityItem, InternalModel):
    activity_id: uuid.UUID
    id: uuid.UUID


class ActivityItemPublic(BaseActivityItem, PublicModel):
    id: uuid.UUID


class ActivityItemDetail(ActivityItem):
    question: str  # type: ignore[assignment]


class ActivityItemDetailPublic(ActivityItemPublic):
    question: str  # type: ignore[assignment]
