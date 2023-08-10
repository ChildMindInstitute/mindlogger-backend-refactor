from apps.shared.exception import BaseError


class FormatldException(BaseError):
    message = "Formatld Exception"


class EmptyAppletException(BaseError):
    message = "Applet is empty"
