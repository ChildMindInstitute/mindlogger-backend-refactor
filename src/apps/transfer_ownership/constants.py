from enum import StrEnum


class TransferOwnershipStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    DECLINED = "declined"
