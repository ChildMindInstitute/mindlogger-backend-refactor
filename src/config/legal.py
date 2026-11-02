from pydantic import BaseModel, field_validator


class LegalSettings(BaseModel):
    # Current MSA version (the date the MSA was finalized), set per environment
    msa_version: str

    @field_validator("msa_version")
    @classmethod
    def check_msa_version(cls, v: str) -> str:
        if not v:
            raise ValueError("Please specify LEGAL__MSA_VERSION variable")
        return v
