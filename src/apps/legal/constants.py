from enum import StrEnum


class LegalDocType(StrEnum):
    MSA = "msa"


class AcceptanceSource(StrEnum):
    SIGNUP = "signup"
    LOGIN_PROMPT = "login_prompt"


class MsaStatus(StrEnum):
    ACCEPTED = "accepted"
    GRACE = "grace"
    REQUIRED = "required"
