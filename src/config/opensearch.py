from pydantic import BaseModel


class OpenSearchSettings(BaseModel):
    """Configure OpenSearch settings"""

    host: str = "opensearch"
    port: int = 9200
    user: str = "admin"
    password: str = "admin"
    use_ssl: bool = True
    verify_certs: bool = False
    audit_index: str = "audit-logs"

    @property
    def url(self) -> str:
        protocol = "https" if self.use_ssl else "http"
        return f"{protocol}://{self.host}:{self.port}"