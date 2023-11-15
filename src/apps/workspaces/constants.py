import enum


class StorageType(str, enum.Enum):
    AWS = "aws"
    AZURE = "azure"
    GCP = "gcp"

    def __str__(self):
        return self.value
