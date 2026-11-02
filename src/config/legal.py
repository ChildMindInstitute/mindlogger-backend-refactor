import datetime

from pydantic import BaseModel


class LegalSettings(BaseModel):
    msa_version: str = "YYYY-MM-DD"  # TODO: set to the current MSA date before merge
    # Day the MSA starts being enforced in admin; unset keeps enforcement off
    msa_effective_from: datetime.date | None = None
    msa_grace_days: int = 60
    # Accounts created before this day get the grace period; defaults to msa_effective_from
    msa_grace_signup_cutoff: datetime.date | None = None
