import base64

from pydantic import BaseModel


class FirebaseCloudMessagingSettings(BaseModel):
    """Configure FCM notification settings"""

    type: str | None
    project_id: str | None
    private_key_id: str | None
    private_key: str | None
    client_email: str | None
    client_id: str | None
    auth_uri: str | None
    token_uri: str | None
    auth_provider_x509_cert_url: str | None
    client_x509_cert_url: str | None
    universe_domain: str | None
    ttl: int = 7 * 24 * 60 * 60

    @property
    def certificate(self) -> dict:
        return dict(
            type=self.type,
            project_id=self.project_id,
            private_key_id=self.private_key_id,
            private_key=base64.b64decode(self.private_key.encode()).decode()
            if self.private_key
            else None,
            client_email=self.client_email,
            client_id=self.client_id,
            auth_uri=self.auth_uri,
            token_uri=self.token_uri,
            auth_provider_x509_cert_url=self.auth_provider_x509_cert_url,
            client_x509_cert_url=self.client_x509_cert_url,
            universe_domain=self.universe_domain,
        )
