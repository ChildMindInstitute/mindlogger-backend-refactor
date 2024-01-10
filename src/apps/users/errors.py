from gettext import gettext as _

from apps.shared.exception import NotFoundError, ValidationError


class UserNotFound(NotFoundError):
    message = _("User not found.")


class UserAlreadyExistError(ValidationError):
    message = _(
        "That email address is already associated with a MindLogger account."
    )


class EmailAddressError(ValidationError):
    message = _("That email is not associated with a MindLogger account.")


class EmailAddressNotValid(ValidationError):
    message_is_template: bool = True
    message = _("Email address: {email} is not valid.")


class PasswordRecoveryKeyNotFound(NotFoundError):
    message = _("Password recovery key not found.")


class PasswordHasSpacesError(NotFoundError):
    message = _("Password should not contain blank spaces")


class UserIsDeletedError(NotFoundError):
    message = _("User is deleted.")


class UserDeviceNotFound(NotFoundError):
    message = _("User device is not found.")


class UsersError(ValidationError):
    message_is_template: bool = True
    message = _("Can not make the looking up by {key} {value}.")


class ReencryptionInProgressError(ValidationError):
    message = _("Cannot change password. Reencryption process in progress.")
