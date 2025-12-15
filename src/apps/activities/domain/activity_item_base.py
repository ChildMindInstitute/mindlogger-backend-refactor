from typing import Annotated, Self, cast

from pydantic import BaseModel, Field, field_validator, model_validator
from pydantic_core.core_schema import ValidationInfo

from apps.activities.domain.conditional_logic import ConditionalLogic
from apps.activities.domain.response_type_config import (
    MultiSelectionConfig,
    MultiSelectionRowsConfig,
    ResponseType,
    ResponseTypeConfig,
    SingleSelectionConfig,
    SingleSelectionRowsConfig,
    SliderConfig,
    SliderRowsConfig,
)
from apps.activities.domain.response_values import (
    MultiSelectionRowsValues,
    MultiSelectionValues,
    ResponseTypeValueConfig,
    ResponseValueConfig,
    SingleSelectionRowsValues,
    SingleSelectionValues,
    SliderRowsValues,
    SliderValues,
)
from apps.activities.errors import (
    AlertFlagMissingSingleMultiRowItemError,
    AlertFlagMissingSliderItemError,
    DataMatrixRequiredError,
    HiddenWhenConditionalLogicSetError,
    IncorrectConfigError,
    IncorrectNameCharactersError,
    IncorrectResponseValueError,
    NullScoreError,
    ScoreRequiredForResponseValueError,
    SliderMinMaxValueError,
    SliderRowsValueError,
)
from apps.shared.domain.custom_validations import sanitize_string
from apps.shared.exception import BaseError


class BaseActivityItem(BaseModel):
    """Please check contracts for exact types of config and response_values fields: <a href="https://mindlogger.atlassian.net/wiki/spaces/MINDLOGGER1/pages/182583316/Activity+item+contracts"> here</a>"""  # noqa: E501

    question: Annotated[dict[str, str], Field(default_factory=dict)]
    response_type: ResponseType
    # smart_union ?
    response_values: Annotated[ResponseValueConfig | None, Field(None, discriminator="type")]
    config: Annotated[ResponseTypeConfig, Field(..., discriminator="type")]
    name: str
    is_hidden: bool | None = False
    conditional_logic: ConditionalLogic | None = None
    allow_edit: bool | None = None

    # model_config = ConfigDict(
    #     json_schema_extra={
    #         "example": {
    #             "question": {"en": "foo"},
    #             "response_type": "text",
    #             "response_values": None,
    #             "config": {
    #                 "remove_back_button": False,
    #                 "skippable_item": False,
    #                 "max_response_length": 300,
    #                 "correct_answer_required": False,
    #                 "correct_answer": None,
    #                 "numerical_response_required": False,
    #                 "response_data_identifier": False,
    #                 "response_required": False,
    #             },
    #             "name": "foo_text",
    #             "is_hidden": False,
    #         },
    #     },
    # )

    @field_validator("name")
    @classmethod
    def validate_name(cls, value):
        # name must contain only alphanumeric symbols or underscore
        value = value.replace(" ", "")  # TODO: remove after migration
        if not value.replace("_", "").replace("-", "").isalnum():
            raise IncorrectNameCharactersError()
        return value

    @field_validator("response_type", mode="before")
    @classmethod
    def validate_response_type(cls, value):
        if value not in ResponseTypeValueConfig:
            raise IncorrectResponseValueError(type=ResponseType)
        return value

    @field_validator("config", mode="before")
    @classmethod
    def validate_config(cls, value, info: ValidationInfo):
        response_type = info.data.get("response_type")
        # response type is checked in separate validator
        if not response_type:
            return value
        # wrap value in class to validate and pass value
        if type(value) is not ResponseTypeValueConfig[response_type]["config"]:
            try:
                value["type"] = response_type
                value = ResponseTypeValueConfig[response_type]["config"](**value)
            except Exception:
                raise IncorrectConfigError(type=ResponseTypeValueConfig[response_type]["config"])

        return value

    @field_validator("response_values", mode="before")
    @classmethod
    def validate_response_values(cls, value, info: ValidationInfo):
        response_type = info.data.get("response_type")
        if not response_type:
            return value
        if response_type not in ResponseType.get_non_response_types():
            if type(value) is not ResponseTypeValueConfig[response_type]["value"]:
                try:
                    value["type"] = response_type
                    value = ResponseTypeValueConfig[response_type]["value"](**value)
                except BaseError as e:
                    raise e
                except Exception:
                    raise IncorrectResponseValueError(type=ResponseTypeValueConfig[response_type]["value"])
        elif value is not None:
            raise IncorrectResponseValueError(type=ResponseTypeValueConfig[response_type]["value"])
        return value

    @field_validator("question")
    @classmethod
    def validate_question(cls, value):
        if isinstance(value, dict):
            for key in value:
                value[key] = sanitize_string(value[key])
        elif isinstance(value, str):
            value = sanitize_string(value)
        return value

    @model_validator(mode="after")
    def validate_score_required(self) -> Self:
        # validate score fields of response values for each response type

        response_type = self.response_type
        response_values = self.response_values
        config = self.config

        if response_type in [
            ResponseType.SINGLESELECT,
            ResponseType.MULTISELECT,
        ]:
            # if add_scores is True in config,
            # then score must be provided in each option of response_values
            response_values = cast(SingleSelectionValues | MultiSelectionValues, response_values)
            config = cast(SingleSelectionConfig | MultiSelectionConfig, config)
            if config.add_scores:
                scores = [option.score for option in response_values.options]
                if None in scores:
                    raise ScoreRequiredForResponseValueError()

        if response_type == ResponseType.SLIDER:
            # if add_scores is True in config, then scores should not be None
            response_values = cast(SliderValues, response_values)
            config = cast(SliderConfig, config)
            if config.add_scores and response_values.scores is None:
                raise NullScoreError()

        if response_type == ResponseType.SLIDERROWS:
            # if add_scores is True in config, then scores should not be None
            response_values = cast(SliderRowsValues, response_values)
            config = cast(SliderRowsConfig, config)
            if config.add_scores:
                for row in response_values.rows:
                    if row.scores is None:
                        raise NullScoreError()

        if response_type in [
            ResponseType.SINGLESELECTROWS,
            ResponseType.MULTISELECTROWS,
        ]:
            # data_matrix must be not null if add_scores or set_alerts are set
            response_values = cast(SingleSelectionRowsValues | MultiSelectionRowsValues, response_values)
            config = cast(SingleSelectionRowsConfig | MultiSelectionRowsConfig, config)
            if config.add_scores or config.set_alerts:
                if response_values.data_matrix is None:
                    raise DataMatrixRequiredError()

        return self

    @model_validator(mode="after")
    def validate_is_hidden(self) -> Self:
        # cannot hide if conditional logic is set
        value = self.is_hidden
        if value and self.conditional_logic:
            raise HiddenWhenConditionalLogicSetError()
        return self

    @model_validator(mode="after")
    def validate_slider_value_alert(self) -> Self:
        # validate slider value alert
        response_type = self.response_type
        config = self.config
        response_values = self.response_values
        if response_type == ResponseType.SLIDER:
            response_values = cast(SliderValues, response_values)
            config = cast(SliderConfig, config)
            if response_values.alerts is not None:
                if not config.set_alerts:
                    raise AlertFlagMissingSliderItemError()

                for alert in response_values.alerts:
                    if config.continuous_slider:
                        if alert.min_value is None or alert.max_value is None:
                            raise SliderMinMaxValueError()
                    else:
                        if alert.value is None:
                            raise SliderMinMaxValueError()

        elif response_type == ResponseType.SLIDERROWS:
            response_values = cast(SliderRowsValues, response_values)
            config = cast(SliderRowsConfig, config)
            for row in response_values.rows:
                if row.alerts is not None:
                    for alert in row.alerts:
                        if alert.value is None:
                            raise SliderRowsValueError()
                        if alert.value is not None and not config.set_alerts:
                            raise AlertFlagMissingSliderItemError()

        return self

    @model_validator(mode="after")
    def validate_single_multi_alert(self) -> Self:
        # validate single/multi selection type alerts
        response_type = self.response_type
        config = self.config
        response_values = self.response_values
        if response_type in [
            ResponseType.SINGLESELECT,
            ResponseType.MULTISELECT,
        ]:
            response_values = cast(SingleSelectionValues | MultiSelectionValues, response_values)
            config = cast(SingleSelectionConfig | MultiSelectionConfig, config)
            for option in response_values.options:
                if option.alert is not None and not config.set_alerts:
                    raise AlertFlagMissingSingleMultiRowItemError()

        if response_type in [
            ResponseType.SINGLESELECTROWS,
            ResponseType.MULTISELECTROWS,
        ]:
            response_values = cast(SingleSelectionRowsValues | MultiSelectionRowsValues, response_values)
            config = cast(SingleSelectionRowsConfig | MultiSelectionRowsConfig, config)
            if response_values.data_matrix is not None:
                for data in response_values.data_matrix:
                    for data_option in data.options:
                        if data_option.alert is not None and not config.set_alerts:
                            raise AlertFlagMissingSingleMultiRowItemError()
        return self
