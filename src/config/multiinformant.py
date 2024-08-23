from pydantic import BaseModel


class MultiInformantSettings(BaseModel):
    temp_relation_expiry_secs: int = 86400
