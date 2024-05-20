from apps.activities.errors import InvalidRawScoreSubscaleError, InvalidScoreSubscaleError


def validate_score_subscale_table(value: str):
    # make sure it's format is "x~y" or "x"
    if "~" not in value:
        if not value.isnumeric():
            raise InvalidScoreSubscaleError()

    if "~" in value:
        # make sure x and y are integers
        x: str | float
        y: str | float
        x, y = value.split("~")
        try:
            x = float(x)  # noqa: F841
            y = float(y)  # noqa: F841

            if len(str(x).split(".")[1]) > 5 or len(str(x).split(".")[1]) > 5:
                raise InvalidScoreSubscaleError()
        except ValueError:
            raise InvalidScoreSubscaleError()

    return value


def validate_raw_score_subscale(value: str):
    # make sure it's format is "x~y" or "x"
    if "~" not in value:
        if not value.lstrip("-").isnumeric():
            raise InvalidRawScoreSubscaleError()

    if "~" in value:
        # make sure x and y are integers
        x: str | int
        y: str | int
        x, y = value.split("~")
        try:
            x = int(x.lstrip("-"))  # noqa: F841
            y = int(y.lstrip("-"))  # noqa: F841
        except ValueError:
            raise InvalidRawScoreSubscaleError()

    return value
