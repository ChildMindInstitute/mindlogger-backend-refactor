from gettext import gettext as _

from apps.shared.exception import InternalServerError, NotFoundError, ValidationError


class LorisServerError(ValidationError):
    message = _("Loris server error {message}.")


class ConsentNotFoundError(NotFoundError):
    message = _("No such consent with {key}={value}.")


class ConsentError(InternalServerError):
    message = _("Consent service error.")


class MlLorisUserRelationshipNotFoundError(NotFoundError):
    message = _("No such user relationship with {key}={value}.")


class MlLorisUserRelationshipError(InternalServerError):
    message = _("MlLorisUserRelationship service error.")


class LorisBadCredentialsError(ValidationError):
    message = _("Provided Loris authentication details (hostname, username or password) are invalid.")


class LorisInvalidTokenError(ValidationError):
    message = _(
        "Received unexpected response from Loris Server."
        " Either the resource is invalid or the received token during"
        " login is wrong although the authentication was correct."
    )


class LorisInvalidHostname(ValidationError):
    message = _("The specified hostname `{hostname}` is not a valid URL")
