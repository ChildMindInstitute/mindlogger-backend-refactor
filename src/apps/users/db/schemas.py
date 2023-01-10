import sqlalchemy as sa

from infrastructure.database.base import Base


class UserSchema(Base):
    __tablename__ = "users"

    email = sa.Column(sa.String(length=100), unique=True)
    full_name = sa.Column(sa.String(length=100))
    hashed_password = sa.Column(sa.String(length=100))
