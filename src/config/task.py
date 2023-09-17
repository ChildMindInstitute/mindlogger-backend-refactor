from pydantic import BaseModel


class AnswerEncryption(BaseModel):
    batch_limit: int = 1000
