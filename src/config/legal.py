from pydantic import BaseModel


class LegalSettings(BaseModel):
    msa_version: str = "YYYY-MM-DD"  # TODO: set to the current MSA date before merge
