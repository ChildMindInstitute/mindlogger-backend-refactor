from enum import StrEnum

# The MSA day starts at 3am Eastern, so cut-offs land overnight for US users
MSA_DAY_TIMEZONE = "America/New_York"
MSA_DAY_ROLLOVER_HOURS = 3


class LegalDocType(StrEnum):
    MSA = "msa"


class AcceptanceSource(StrEnum):
    SIGNUP = "signup"
    LOGIN_PROMPT = "login_prompt"


class MsaStatus(StrEnum):
    ACCEPTED = "accepted"
    GRACE = "grace"
    REQUIRED = "required"
