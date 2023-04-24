from pydantic import BaseModel, Field, root_validator, validator

from apps.activities.domain.response_type_config import (
    NoneResponseType,
    ResponseType,
    ResponseTypeConfig,
    ResponseTypeValueConfig,
)
from apps.activities.domain.response_values import ResponseValueConfig
from apps.shared.errors import ValidationError


class BaseActivityItem(BaseModel):
    question: dict[str, str] = Field(default_factory=dict)
    response_type: ResponseType
    response_values: ResponseValueConfig | None = Field(default=None)
    config: ResponseTypeConfig
    name: str
    is_hidden: bool | None = False

    @validator("name")
    def validate_name(cls, value):
        # name must contain only alphanumeric symbols or underscore
        if not value.replace("_", "").isalnum():
            raise ValidationError(
                message="Name must contain only alphanumeric symbols or underscore"  # noqa: E501
            )
        return value

    @validator("config", pre=True)
    def validate_config(cls, value, values, **kwargs):
        response_type = values.get("response_type")
        if not ResponseTypeValueConfig[response_type]["config"].parse_obj(
            value
        ):
            raise ValidationError(
                message=f"config must be of type {ResponseTypeValueConfig[response_type]['config']}"  # noqa: E501
            )
        return value

    @root_validator()
    def validate_response_type(cls, values):
        response_type = values.get("response_type")
        response_values = values.get("response_values")

        if response_type in ResponseTypeValueConfig:
            if response_type not in list(NoneResponseType):
                if not isinstance(
                    response_values,
                    ResponseTypeValueConfig[response_type]["value"],
                ):
                    raise ValidationError(
                        message=f"response_values must be of type {ResponseTypeValueConfig[response_type]['value']}"  # noqa: E501
                    )
            else:
                if response_values is not None:
                    raise ValidationError(
                        message=f"response_values must be of type {ResponseTypeValueConfig[response_type]['value']}"  # noqa: E501
                    )
        else:
            raise ValidationError(
                message=f"response_type must be of type {ResponseType}"
            )
        return values

    @root_validator()
    def validate_score_required(cls, values):
        # validate score fields of response values for each response type

        response_type = values.get("response_type")
        response_values = values.get("response_values")
        config = values.get("config")

        if response_type in [
            ResponseType.SINGLESELECT,
            ResponseType.MULTISELECT,
        ]:
            # if add_scores is True in config, then score must be provided in each option of response_values  # noqa: E501
            if config.add_scores:
                scores = [option.score for option in response_values.options]
                if None in scores:
                    raise ValidationError(
                        message="score must be provided in each option of response_values"  # noqa: E501
                    )

        if response_type is ResponseType.SLIDER:
            # if add_scores is True in config, then length of scores must be equal to max_value - min_value + 1 and must not include None  # noqa: E501
            if config.add_scores:
                if len(response_values.scores) != (
                    response_values.max_value - response_values.min_value + 1
                ):
                    raise ValidationError(
                        message="scores must be provided for each value"  # noqa: E501
                    )
                if None in response_values.scores:
                    raise ValidationError(
                        message="scores must not include None values"  # noqa: E501
                    )

        if response_type is ResponseType.SLIDERROWS:
            # if add_scores is True in config, then length of scores in each row must be equal to max_value - min_value + 1 of each row and must not include None  # noqa: E501
            if config.add_scores:
                for row in response_values.rows:
                    if len(row.scores) != (row.max_value - row.min_value + 1):
                        raise ValidationError(
                            message="scores must be provided for each value"  # noqa: E501
                        )
                    if None in row.scores:
                        raise ValidationError(
                            message="scores must not include None values"  # noqa: E501
                        )

        if response_type in [
            ResponseType.SINGLESELECTROWS,
            ResponseType.MULTISELECTROWS,
        ]:
            # if add_scores is True in config, then score must be provided in each option of each row of response_values  # noqa: E501
            if config.add_scores:
                for row in response_values.rows:
                    scores = [option.score for option in row.options]
                    if None in scores:
                        raise ValidationError(
                            message="score must be provided in each option of response_values"  # noqa: E501
                        )

        return values
