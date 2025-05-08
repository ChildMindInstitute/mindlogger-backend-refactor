from pydantic import BaseModel


class OneUpHealthSettings(BaseModel):
    client_id: str | None = None
    client_secret: str | None = None
    base_url: str = "https://api.1up.health"
    auth_base_url: str = "https://auth.1up.health"
    base_backoff_delay: int = 5
    max_backoff_delay: int = 60 * 60 * 24
    max_error_retries: int = 5
