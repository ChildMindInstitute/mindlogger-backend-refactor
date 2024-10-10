import uuid

import pytest
from pydantic import ValidationError

from apps.shared.bcrypt import verify
from apps.shared.hashing import hash_sha224
from apps.users import domain, errors

BaseData = dict[str, str]


@pytest.fixture
def base_data() -> BaseData:
    return {
        "first_name": "first_name",
        "last_name": "last_name",
        "email": "email@example.com",
        "password": "password",
    }


def test_user_create_request(base_data: BaseData):
    user = domain.UserCreateRequest(**base_data)
    for k, v in base_data.items():
        assert v == getattr(user, k)


def test_user_create_request_email_to_lower_case(base_data: BaseData):
    base_data["email"] = base_data["email"].upper()
    user = domain.UserCreateRequest(**base_data)
    assert user.email == base_data["email"].lower()


def test_user_create_request_white_space_is_not_allowed_in_password(
    base_data: BaseData,
):
    base_data["password"] = "pass word"
    with pytest.raises(errors.PasswordHasSpacesError):
        domain.UserCreateRequest(**base_data)


def test_user_create_request_not_valid_email(
    base_data: BaseData,
):
    base_data["email"] = "email@email@com.com"
    with pytest.raises(ValidationError):
        domain.UserCreateRequest(**base_data)


def test_user_create_computed_fields(base_data: BaseData):
    user = domain.UserCreate(**base_data)
    for k, v in base_data.items():
        assert v == getattr(user, k)
    # Use verify
    # because get_password_hash returns always different hash on each call
    assert verify(base_data["password"], user.hashed_password)
    assert user.hashed_email == hash_sha224(base_data["email"])


def test_public_user_from_user_model(base_data: BaseData):
    user_create = domain.UserCreate(**base_data)
    user = domain.User(
        email=user_create.hashed_email,
        first_name=user_create.first_name,
        last_name=user_create.last_name,
        id=uuid.uuid4(),
        is_super_admin=False,
        hashed_password=user_create.hashed_password,
        email_encrypted=user_create.email,
    )
    public_user = domain.PublicUser.from_user(user)
    assert public_user.email == user.email_encrypted
    assert public_user.first_name == user.first_name
    assert public_user.last_name == user.last_name
    assert public_user.id == user.id


@pytest.mark.parametrize("field, value", (("password", "pass word"), ("prev_password", "pass word")))
def test_change_password_passwords_contain_whitespace(field: str, value: str):
    data = {"password": "password", "prev_password": "prev_password"}
    data[field] = value
    with pytest.raises(errors.PasswordHasSpacesError):
        domain.ChangePasswordRequest(**data)


def test_create_user_model_with_extra_fields__extra_field_ignored(
    base_data: BaseData,
):
    base_data["confirm_password"] = "confirm_passsword"
    user = domain.UserCreateRequest(**base_data)
    assert not hasattr(user, "confirm_password")


def test_user_get_full_name(base_data: BaseData):
    user = domain.User(
        email=base_data["email"],
        first_name="John",
        last_name="Doe",
        id=uuid.uuid4(),
        is_super_admin=False,
        hashed_password=base_data["password"],
    )
    assert user.get_full_name() == "John Doe"


def test_user_get_full_name__no_last_name(base_data: BaseData):
    user = domain.User(
        email=base_data["email"],
        first_name="John",
        last_name="",
        id=uuid.uuid4(),
        is_super_admin=False,
        hashed_password=base_data["password"],
    )
    assert user.get_full_name() == "John"
