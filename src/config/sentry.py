from pydantic import BaseModel


class SentrySettings(BaseModel):
    dsn: str = ""
