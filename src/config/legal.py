import datetime

from pydantic import BaseModel, field_validator


class LegalSettings(BaseModel):
    # Current MSA version (the date the MSA was finalized), set per environment
    msa_version: str
    # Day the MSA starts being enforced in admin; unset keeps enforcement off
    msa_effective_from: datetime.date | None = None
    msa_grace_days: int = 60
    # Accounts created before this day get the grace period; defaults to msa_effective_from
    msa_grace_signup_cutoff: datetime.date | None = None

    @field_validator("msa_version")
    @classmethod
    def check_msa_version(cls, v: str) -> str:
        if not v:
            raise ValueError("Please specify LEGAL__MSA_VERSION variable")
        return v
