from gettext import gettext as _

from apps.shared.exception import NotFoundError, ValidationError


class UserNotFound(NotFoundError):
    message = _("User not found.")


class UserAlreadyExistError(ValidationError):
    message = _("That email address is already associated with a Curious account.")


class PasswordRecoveryKeyNotFound(NotFoundError):
    message = _("Password recovery key not found.")


class PasswordHasSpacesError(ValidationError):
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


class MFASetupNotFoundError(NotFoundError):
    message = _("No pending MFA setup found. Please initiate MFA setup first.")


class MFASetupExpiredError(ValidationError):
    message = _("MFA setup has expired. Please initiate MFA setup again.")


class InvalidTOTPCodeError(ValidationError):
    message = _("Invalid TOTP code. Please check your authenticator app and try again.")
