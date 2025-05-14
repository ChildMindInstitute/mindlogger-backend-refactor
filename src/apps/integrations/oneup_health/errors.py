from gettext import gettext as _

from starlette import status

from apps.shared.exception import BaseError, ExceptionTypes


class OneUpHealthErrorCodes:
    USER_ALREADY_EXISTS = "USER_ALREADY_EXISTS"
    GEOGRAPHIC_RESTRICTION = "GEOGRAPHIC_RESTRICTION"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"


class OneUpHealthAPIError(BaseError):
    message = _("1UpHealth request failed.")
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR

    def __init__(self, message=None, **kwargs):
        if message:
            super().__init__(message, **kwargs)
        else:
            super().__init__(**kwargs)


class OneUpHealthUserAlreadyExists(OneUpHealthAPIError):
    message = _("1UpHealth user already exists for this subject.")
    type = ExceptionTypes.UNDEFINED
    status_code = status.HTTP_409_CONFLICT
    error_code = OneUpHealthErrorCodes.USER_ALREADY_EXISTS


class OneUpHealthTokenExpiredError(OneUpHealthAPIError):
    message = _("1UpHealth access token has expired.")
    type = ExceptionTypes.ACCESS_DENIED
    status_code = status.HTTP_401_UNAUTHORIZED
    error_code = OneUpHealthErrorCodes.TOKEN_EXPIRED


class OneUpHealthAPIForbiddenError(OneUpHealthAPIError):
    message = _("Access to 1UpHealth is currently restricted to users within the United States.")
    type = ExceptionTypes.ACCESS_DENIED
    status_code = status.HTTP_403_FORBIDDEN
    error_code = OneUpHealthErrorCodes.GEOGRAPHIC_RESTRICTION


class OneUpHealthServiceUnavailableError(OneUpHealthAPIError):
    message = _("1UpHealth service is currently unavailable.")
    type = ExceptionTypes.UNDEFINED
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    error_code = OneUpHealthErrorCodes.SERVICE_UNAVAILABLE


OneUpHealthAPIErrorMessageMap = {
    "this user already exists": OneUpHealthUserAlreadyExists,
    "service unavailable": OneUpHealthServiceUnavailableError,
    "token expired": OneUpHealthTokenExpiredError,
}
