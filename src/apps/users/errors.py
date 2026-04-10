from gettext import gettext as _

from apps.authentication.constants import AuthErrorCode
from apps.shared.exception import AccessDeniedError, NotFoundError, ValidationError


class UserNotFound(NotFoundError):
    message = _("User not found.")


class UserAlreadyExistError(ValidationError):
    message = _("That email address is already associated with a Curious account.")


class PasswordRecoveryKeyNotFound(NotFoundError):
    message = _("Password recovery key not found.")


class PasswordHasSpacesError(ValidationError):
    message = _("Password must not contain spaces.")


class PasswordContainsInvalidCharactersError(ValidationError):
    message = _("Password must not contain control characters.")


class PasswordTooShortError(ValidationError):
    message_is_template: bool = True
    message = _("Password must be at least {chars} characters.")


class PasswordInsufficientTypesError(ValidationError):
    message_is_template: bool = True
    message = _("Password must contain at least {types} of: uppercase, lowercase, number, symbol")


class PasswordTooCommonError(ValidationError):  # Phase 2
    message = _("Password is too common or easily guessable.")


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

    def __init__(
        self,
        session_attempts_remaining: int | None = None,
        global_attempts_remaining: int | None = None,
        **kwargs,
    ):
        metadata: dict[str, int] = {}
        if session_attempts_remaining is not None:
            metadata["session_attempts_remaining"] = session_attempts_remaining
        if global_attempts_remaining is not None:
            metadata["global_attempts_remaining"] = global_attempts_remaining
        super().__init__(metadata=metadata if metadata else None, **kwargs)


class MFAAlreadyEnabledError(ValidationError):
    message = _("Two-factor authentication is already enabled for your account.")


class MFANotEnabledError(AccessDeniedError):
    message = _("MFA is not enabled for this account.")


class RecoveryCodesNotFoundError(NotFoundError):
    message = _("No recovery codes found. Please enable MFA to generate recovery codes.")


class RecoveryCodeInvalidError(ValidationError):
    message = _("Invalid recovery code. Please check the code and try again.")
    error_code = AuthErrorCode.MFA_INVALID_RECOVERY_CODE


class RecoveryCodeAlreadyUsedError(ValidationError):
    message = _("This recovery code has already been used. Each code can only be used once.")


class RecoveryCodeNotFoundError(NotFoundError):
    message = _("No matching recovery code found. Please verify the code is correct.")


class MFASessionPurposeMismatchError(ValidationError):
    message = _("Invalid MFA session for this operation.")
