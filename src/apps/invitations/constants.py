from enum import StrEnum


class InvitationStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    DECLINED = "declined"


INVITATION_ROLE_TRANSLATIONS: dict[str, dict[str, str]] = {
    "respondent": {
        "af": "respondent",
        "xh": "umphenduli",
        "zu": "ophendulayo",
    },
}
