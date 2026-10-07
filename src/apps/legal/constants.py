from enum import StrEnum


class LegalDocType(StrEnum):
    MSA = "msa"


class AcceptanceSource(StrEnum):
    SIGNUP = "signup"


class MsaStatus(StrEnum):
    ACCEPTED = "accepted"
    GRACE = "grace"
    REQUIRED = "required"
