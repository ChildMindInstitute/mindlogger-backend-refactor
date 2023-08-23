from pydantic import BaseModel, Field, root_validator, validator

from apps.activities.domain.conditional_logic import ConditionalLogic
from apps.activities.domain.response_type_config import (
    NoneResponseType,
    ResponseType,
    ResponseTypeValueConfig,
)
from apps.activities.errors import (
    AlertFlagMissingSingleMultiRowItemError,
    AlertFlagMissingSliderItemError,
    DataMatrixRequiredError,
    HiddenWhenConditionalLogicSetError,
    IncorrectConditionLogicItemTypeError,
    IncorrectConfigError,
    IncorrectNameCharactersError,
    IncorrectResponseValueError,
    NullScoreError,
    ScoreRequiredForResponseValueError,
    ScoreRequiredForValueError,
    SliderMinMaxValueError,
    SliderRowsValueError,
)
from apps.shared.domain import PublicModel
from apps.shared.exception import BaseError


class BaseActivityItem(BaseModel):
    """Please check contracts for exact types of config and response_values fields: <a href="https://mindlogger.atlassian.net/wiki/spaces/MINDLOGGER1/pages/182583316/Activity+item+contracts"> here</a>"""  # noqa: E501

    question: dict[str, str] = Field(default_factory=dict)
    response_type: ResponseType
    response_values: PublicModel | None  # ResponseValueConfig
    config: PublicModel  # ResponseTypeConfig
    name: str
    is_hidden: bool | None = False
    conditional_logic: ConditionalLogic | None = None
    allow_edit: bool | None = None

    # class Config:
    #     schema_extra = {
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
    #     }

    @validator("name")
    def validate_name(cls, value):
        # name must contain only alphanumeric symbols or underscore
        value = value.replace(" ", "")  # TODO: remove after migration
        if not value.replace("_", "").replace("-", "").isalnum():
            raise IncorrectNameCharactersError()
        return value

    @validator("config", pre=True)
    def validate_config(cls, value, values):
        response_type = values.get("response_type")
        # wrap value in class to validate and pass value
        if response_type in ResponseTypeValueConfig:
            if (
                type(value)
                is not ResponseTypeValueConfig[response_type]["config"]
            ):
                try:
                    value = ResponseTypeValueConfig[response_type]["config"](
                        **value
                    )
                except Exception:
                    raise IncorrectConfigError(
                        type=ResponseTypeValueConfig[response_type]["config"]
                    )
        else:
            raise IncorrectResponseValueError(type=ResponseType)

        return value

    @validator("response_values", pre=True)
    def validate_response_type(cls, value, values):
        response_type = values.get("response_type")
        if response_type in ResponseTypeValueConfig:
            if response_type not in list(NoneResponseType):
                if (
                    type(value)
                    is not ResponseTypeValueConfig[response_type]["value"]
                ):
                    try:
                        value = ResponseTypeValueConfig[response_type][
                            "value"
                        ](**value)
                    except BaseError as e:
                        raise e
                    except Exception:
                        raise IncorrectResponseValueError(
                            type=ResponseTypeValueConfig[response_type][
                                "value"
                            ]
                        )
            else:
                if (
                    value is not None
                    and type(value)
                    is not ResponseTypeValueConfig[response_type]["value"]
                ):
                    raise IncorrectResponseValueError(
                        type=ResponseTypeValueConfig[response_type]["value"]
                    )
                elif (
                    type(value)
                    is ResponseTypeValueConfig[response_type]["value"]
                ):
                    value = None

        else:
            raise IncorrectResponseValueError(type=ResponseType)
        return value

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
            # if add_scores is True in config,
            # then score must be provided in each option of response_values
            if config.add_scores:
                scores = [option.score for option in response_values.options]
                if None in scores:
                    raise ScoreRequiredForResponseValueError()

        if response_type is ResponseType.SLIDER:
            # if add_scores is True in config,
            # then length of scores must be equal
            # to max_value - min_value + 1 and must not include None
            if config.add_scores:
                if len(response_values.scores) != (
                    response_values.max_value - response_values.min_value + 1
                ):
                    raise ScoreRequiredForValueError()
                if None in response_values.scores:
                    raise NullScoreError()

        if response_type is ResponseType.SLIDERROWS:
            # if add_scores is True in config,
            # then length of scores in each row must be
            # equal to max_value - min_value + 1 of each row
            # and must not include None
            if config.add_scores:
                for row in response_values.rows:
                    if len(row.scores) != (row.max_value - row.min_value + 1):
                        raise ScoreRequiredForValueError()
                    if None in row.scores:
                        raise NullScoreError()

        if response_type in [
            ResponseType.SINGLESELECTROWS,
            ResponseType.MULTISELECTROWS,
        ]:
            # if add_scores is True in config, then score must be provided in each option of each row of response_values  # noqa: E501
            if config.add_scores or config.add_tokens:
                if response_values.data_matrix is None:
                    raise DataMatrixRequiredError()

        return values

    @validator("conditional_logic")
    def validate_conditional_logic(cls, value, values):
        response_type = values.get("response_type")
        if value is not None:
            # check if response type is correct
            if response_type not in [
                ResponseType.SINGLESELECT,
                ResponseType.MULTISELECT,
                ResponseType.SLIDER,
                ResponseType.TEXT,
                ResponseType.TIME,
                ResponseType.TIMERANGE,  # TODO add support???
            ]:
                raise IncorrectConditionLogicItemTypeError()

        return value

    @root_validator()
    def validate_is_hidden(cls, values):
        # cannot hide if conditional logic is set
        value = values.get("is_hidden")
        if value and values.get("conditional_logic"):
            raise HiddenWhenConditionalLogicSetError()
        return values

    @root_validator()
    def validate_slider_value_alert(cls, values):
        # validate slider value alert
        response_type = values.get("response_type")
        config = values.get("config")
        response_values = values.get("response_values")
        if response_type in [
            ResponseType.SLIDER,
        ]:
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

        elif response_type in [
            ResponseType.SLIDERROWS,
        ]:
            for row in response_values.rows:
                if row.alerts is not None:
                    for alert in row.alerts:
                        if alert.value is None:
                            raise SliderRowsValueError()
                        if alert.value is not None and not config.set_alerts:
                            raise AlertFlagMissingSliderItemError()

        return values

    @root_validator()
    def validate_single_multi_alert(cls, values):
        # validate single/multi selection type alerts
        response_type = values.get("response_type")
        config = values.get("config")
        response_values = values.get("response_values")
        if response_type in [
            ResponseType.SINGLESELECT,
            ResponseType.MULTISELECT,
        ]:
            for option in response_values.options:
                if option.alert is not None and not config.set_alerts:
                    raise AlertFlagMissingSingleMultiRowItemError()

        if response_type in [
            ResponseType.SINGLESELECTROWS,
            ResponseType.MULTISELECTROWS,
        ]:
            if response_values.data_matrix is not None:
                for data in response_values.data_matrix:
                    for option in data.options:
                        if option.alert is not None and not config.set_alerts:
                            raise AlertFlagMissingSingleMultiRowItemError()
        return values
