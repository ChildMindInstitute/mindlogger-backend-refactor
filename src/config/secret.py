from pydantic import BaseModel


class SecretSettings(BaseModel):
    key_length: int = 32
    secret_key: str | None = None

    @property
    def key(self) -> bytes:
        if self.secret_key:
            key = bytes.fromhex(self.secret_key)
            if len(key) != self.key_length:
                raise ValueError(f"Key length in bytes should be {self.key_length}")
            return key
        raise ValueError("Please specify SECRETS__SECRET_KEY variable")
