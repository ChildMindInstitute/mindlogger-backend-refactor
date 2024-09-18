from pydantic import ValidationError, PositiveInt

from apps.activities.errors import InvalidAgeSubscaleError, InvalidRawScoreSubscaleError, InvalidScoreSubscaleError


def validate_score_subscale_table(value: str):
    # make sure it's format is "x~y" or "x"
    if "~" not in value:
        # make sure value is float with 5 decimal points
        val: float
        try:
            val = float(value)  # noqa: F841
            if len(str(val).split(".")[1]) > 5:
                raise InvalidScoreSubscaleError()
        except ValueError:
            raise InvalidScoreSubscaleError()

    if "~" in value:
        # make sure x and y are float with 5 decimal points
        x: str | float
        y: str | float
        x, y = value.split("~")
        try:
            x = float(x)  # noqa: F841
            y = float(y)  # noqa: F841

            if len(str(x).split(".")[1]) > 5 or len(str(y).split(".")[1]) > 5:
                raise InvalidScoreSubscaleError()
        except ValueError:
            raise InvalidScoreSubscaleError()

    return value


def validate_age_subscale(value: PositiveInt | str | None):
    # make sure its format is "x~y" or "x"

    def validate_non_negative_int(maybe_int: str):
        try:
            int_value = int(maybe_int)
            if int_value < 0:
                raise InvalidAgeSubscaleError()
        except (ValueError, ValidationError):
            raise InvalidAgeSubscaleError()

    if value is None:
        return value
    elif isinstance(value, int):
        if value < 0:
            raise InvalidAgeSubscaleError()
    elif "~" not in value:
        # make sure value is a positive integer
        validate_non_negative_int(value)
    else:
        # make sure x and y are positive integers
        x: str
        y: str
        x, y = value.split("~")
        validate_non_negative_int(x)
        validate_non_negative_int(y)

    return value


def validate_raw_score_subscale(value: str):
    # make sure it's format is "x~y" or "x"
    if "~" not in value:
        # make sure value is float with 2 decimal points
        val: float
        try:
            val = float(value)  # noqa: F841
            if len(str(val).split(".")[1]) > 2:
                raise InvalidRawScoreSubscaleError()
        except ValueError:
            raise InvalidRawScoreSubscaleError()

    if "~" in value:
        # make sure x and y are float with 2 decimal points
        x: str | float
        y: str | float
        x, y = value.split("~")
        try:
            x = float(x)  # noqa: F841
            y = float(y)  # noqa: F841

            if len(str(x).split(".")[1]) > 2 or len(str(y).split(".")[1]) > 2:
                raise InvalidRawScoreSubscaleError()
        except ValueError:
            raise InvalidRawScoreSubscaleError()

    return value
