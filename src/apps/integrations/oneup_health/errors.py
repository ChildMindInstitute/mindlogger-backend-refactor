from gettext import gettext as _

from apps.shared.exception import BaseError, ExceptionTypes


class OneUpHealthAPIError(BaseError):
    message = _("OneUp Health request failed.")


class OneUpHealthUserAlreadyExists(OneUpHealthAPIError):
    message = _("OneUp Health user already exists for this subject.")


class OneUpHealthAPIForbiddenError(OneUpHealthAPIError):
    message = _("Access to OneUp Health is currently restricted to users within the United States.")
    type = ExceptionTypes.ACCESS_DENIED


OneUpHealthAPIErrorMessageMap = {
    "this user already exists": OneUpHealthUserAlreadyExists,
}
