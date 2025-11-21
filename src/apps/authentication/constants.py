"""Authentication error codes for multi-language support."""


class AuthErrorCode:
    """Error codes for authentication errors.

    These codes are used by frontend applications to display
    localized error messages in multiple languages.
    """

    # MFA related errors
    MFA_INVALID_TOTP_CODE = "AUTH.MFA.INVALID_TOTP_CODE"
    MFA_SESSION_NOT_FOUND = "AUTH.MFA.SESSION_NOT_FOUND"
    MFA_TOO_MANY_ATTEMPTS = "AUTH.MFA.TOO_MANY_ATTEMPTS"
    MFA_GLOBAL_LOCKOUT = "AUTH.MFA.GLOBAL_LOCKOUT"
    MFA_TOKEN_EXPIRED = "AUTH.MFA.TOKEN_EXPIRED"
    MFA_TOKEN_INVALID = "AUTH.MFA.TOKEN_INVALID"
    MFA_TOKEN_MALFORMED = "AUTH.MFA.TOKEN_MALFORMED"

    # General authentication errors
    INVALID_CREDENTIALS = "AUTH.INVALID_CREDENTIALS"
    INVALID_REFRESH_TOKEN = "AUTH.INVALID_REFRESH_TOKEN"
    AUTHENTICATION_ERROR = "AUTH.AUTHENTICATION_ERROR"
    PERMISSIONS_ERROR = "AUTH.PERMISSIONS_ERROR"
    EMAIL_DOES_NOT_EXIST = "AUTH.EMAIL_DOES_NOT_EXIST"
