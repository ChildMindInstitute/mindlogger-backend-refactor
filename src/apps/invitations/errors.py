from apps.shared.enums import Language
from apps.shared.errors import ValidationError
from apps.shared.exception import NotFoundError


class InvitationDoesNotExist(NotFoundError):
    messages = {
        Language.ENGLISH: "Invitation does not exist."
    }


class AppletDoesNotExist(ValidationError):
    def __init__(self, *_, message="Applet does not exist.") -> None:
        super().__init__(message=message)


class DoesNotHaveAccess(ValidationError):
    def __init__(self, *_, message="Access denied.") -> None:
        super().__init__(message=message)


class InvitationAlreadyProcesses(ValidationError):
    def __init__(
            self, *_, message="Invitation has been already processed."
    ) -> None:
        super().__init__(message=message)


class NonUniqueValue(ValidationError):
    def __init__(self, *_, message="Non-unique value.") -> None:
        super().__init__(message=message)


class RespondentDoesNotExist(ValidationError):
    def __init__(
            self, *_, message="Respondent does not exist in applet."
    ) -> None:
        super().__init__(message=message)
