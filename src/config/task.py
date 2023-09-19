from pydantic import BaseModel


class AnswerEncryption(BaseModel):
    batch_limit: int = 1000
    max_retries: int = 5
    retry_timeout: int = 12 * 60 * 60
