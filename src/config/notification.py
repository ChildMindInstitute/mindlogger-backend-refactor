import base64

from pydantic import BaseModel, Field


class FirebaseCloudMessagingSettings(BaseModel):
    """Configure FCM notification settings"""

    type: str | None = None
    project_id: str | None = None
    private_key_id: str | None = None
    private_key: str | None = None
    client_email: str | None = None
    client_id: str | None = None
    auth_uri: str | None = None
    token_uri: str | None = None
    auth_provider_x509_cert_url: str | None = None
    client_x509_cert_url: str | None = None
    universe_domain: str | None = None
    ttl: int = 7 * 24 * 60 * 60
    # Tokens per Firebase call (Firebase allows at most 500); lower it on dev to test batching
    multicast_batch_size: int = Field(default=500, ge=1, le=500)
    # Test only: fail Firebase calls with more tokens than this, to fake the >500 error on dev
    test_token_limit: int | None = Field(default=None, ge=1)

    @property
    def certificate(self) -> dict:
        return dict(
            type=self.type,
            project_id=self.project_id,
            private_key_id=self.private_key_id,
            private_key=base64.b64decode(self.private_key.encode()).decode() if self.private_key else None,
            client_email=self.client_email,
            client_id=self.client_id,
            auth_uri=self.auth_uri,
            token_uri=self.token_uri,
            auth_provider_x509_cert_url=self.auth_provider_x509_cert_url,
            client_x509_cert_url=self.client_x509_cert_url,
            universe_domain=self.universe_domain,
        )
