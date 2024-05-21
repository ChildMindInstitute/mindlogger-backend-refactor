from apps.activities.errors import InvalidRawScoreSubscaleError, InvalidScoreSubscaleError


def validate_score_subscale_table(value: str):
    # make sure it's format is "x~y" or "x"
    if "~" not in value:
        # make sure x is float with 5 decimal points
        x: float
        try:
            x = float(value)  # noqa: F841
            if len(str(x).split(".")[1]) > 5:
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


def validate_raw_score_subscale(value: str):
    # make sure it's format is "x~y" or "x"
    if "~" not in value:
        # make sure x is float with 5 decimal points
        x: float
        try:
            x = float(value)  # noqa: F841
            if len(str(x).split(".")[1]) > 2:
                raise InvalidRawScoreSubscaleError()
        except ValueError:
            raise InvalidRawScoreSubscaleError()

    if "~" in value:
        # make sure x and y are float with 5 decimal points
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
