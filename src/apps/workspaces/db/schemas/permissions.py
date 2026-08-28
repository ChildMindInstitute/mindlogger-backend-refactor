from sqlalchemy import Column, ForeignKey, String, UniqueConstraint

from infrastructure.database.base import Base

__all__ = ["Permissions", "RolePermissions"]


class Permissions(Base):
    __tablename__ = "permissions"
    name = Column(String(length=60), nullable=False, index=True)
    code = Column(String(length=20), nullable=False, index=True)


class RolePermissions(Base):
    __tablename__ = "permissions_roles"
    __table_args__ = (
        UniqueConstraint(
            "role", "permission_id", name="uq_role_permission_id"
        ),
    )

    role = Column(String(length=20), nullable=False, index=True)
    permission_id = Column(
        ForeignKey("permissions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
