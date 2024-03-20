from pydantic import BaseModel


class SecretSettings(BaseModel):
    key_length: int = 64
    secret_key: str | None = None

    @property
    def key(self) -> bytes:
        if self.secret_key and len(self.secret_key) == self.key_length:
            return bytes.fromhex(self.secret_key)
        raise ValueError("Please specify SECRETS__SECRET_KEY variable with length 32 characters")
