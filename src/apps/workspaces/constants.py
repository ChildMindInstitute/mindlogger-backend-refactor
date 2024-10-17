import enum


class StorageType(enum.StrEnum):
    AWS = "aws"
    AZURE = "azure"
    GCP = "gcp"

    def __str__(self):
        return self.value
