from pydantic import BaseModel


class PasswordSettings(BaseModel):
    min_length: int = 10
    min_character_types: int = 3
    zxcvbn_enabled: bool = False  # Phase 2
    hibp_enabled: bool = False  # Phase 2
