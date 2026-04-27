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
        "password": "TestPass123!",
    }


def test_user_create_request(base_data: BaseData):
    user = domain.UserCreateRequest(**base_data)
    for k, v in base_data.items():
        assert v == getattr(user, k)


def test_user_create_request_email_to_lower_case(base_data: BaseData):
    base_data["email"] = base_data["email"].upper()
    user = domain.UserCreateRequest(**base_data)
    assert user.email == base_data["email"].lower()


@pytest.mark.parametrize(
    "password",
    [
        "Test Pass1!",  # ASCII space
        "Test\u00a0Pass1!",  # non-breaking space
        "Test\u2003Pass1!",  # em space
        "Test\u2800Pass1!",  # blank Braille pattern (blank character that Unicode classifies as visible)
    ],
)
def test_user_create_request_whitespace_is_not_allowed_in_password(
    base_data: BaseData,
    password: str,
):
    base_data["password"] = password
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


@pytest.mark.parametrize(
    "password",
    [
        "Abcdefg123",  # 3 types: lower + upper + digit
        "Abcdefgh!@",  # 3 types: lower + upper + symbol
        "abcdefg12!",  # 3 types: lower + digit + symbol
        "ABCDEFG12!",  # 3 types: upper + digit + symbol
        "\u65e5123456789",  # 3 types: lower (via caseless CJK) + upper (via caseless CJK) + digit
        "TestPass1!",  # 4 types: lower + upper + digit + symbol
        "TestPass1!n\u0303",  # 4 types: NFKC normalizes n + combining ~ to ñ
    ],
)
def test_user_create_request_valid_passwords(
    base_data: BaseData,
    password: str,
):
    base_data["password"] = password
    domain.UserCreateRequest(**base_data)


@pytest.mark.parametrize(
    "password",
    [
        "Short1!aa",  # 9 chars
        "weak",  # 4 chars
        "",  # 0 chars
    ],
)
def test_user_create_request_too_short_password_is_not_allowed(
    base_data: BaseData,
    password: str,
):
    base_data["password"] = password
    with pytest.raises(errors.PasswordTooShortError):
        domain.UserCreateRequest(**base_data)


@pytest.mark.parametrize(
    "password",
    [
        "abcdefghij",  # 1 type: lowercase only
        "ABCDEFGHIJ",  # 1 type: uppercase only
        "1234567890",  # 1 type: digit only
        "!@#$%^&*().",  # 1 type: symbol only
        "abcdABCDEF",  # 2 types: lowercase + uppercase
        "abcdefgh12",  # 2 types: lowercase + digit
        "ABCDEFGH12",  # 2 types: uppercase + digit
        "abcdefgh!@",  # 2 types: lowercase + symbol
        "ABCDEFGH!@",  # 2 types: uppercase + symbol
        "1234567890!",  # 2 types: digit + symbol
    ],
)
def test_user_create_request_insufficient_character_types_is_not_allowed(
    base_data: BaseData,
    password: str,
):
    base_data["password"] = password
    with pytest.raises(errors.PasswordInsufficientTypesError):
        domain.UserCreateRequest(**base_data)


@pytest.mark.parametrize(
    "password",
    [
        "TestPass1!\x00",  # null byte (Cc)
        "TestPass1!\u200b",  # zero-width space (Cf)
    ],
)
def test_user_create_request_control_characters_are_not_allowed_in_password(
    base_data: BaseData,
    password: str,
):
    base_data["password"] = password
    with pytest.raises(errors.PasswordContainsInvalidCharactersError):
        domain.UserCreateRequest(**base_data)


@pytest.mark.parametrize(
    "password",
    [
        "TestPass1!\U0001f600",  # grinning face (standard emoji)
        "TestPass1!\U0001f1fa\U0001f1f3",  # flag (regional indicator)
    ],
)
def test_user_create_request_emojis_are_not_allowed_in_password(
    base_data: BaseData,
    password: str,
):
    base_data["password"] = password
    with pytest.raises(errors.PasswordHasEmojisError):
        domain.UserCreateRequest(**base_data)


def test_change_password_new_password_rejects_whitespace(
    base_data: BaseData,
):
    data = {"password": "Test Pass1!", "prev_password": base_data["password"]}
    with pytest.raises(errors.PasswordHasSpacesError):
        domain.ChangePasswordRequest(**data)


def test_change_password_prev_password_allows_whitespace(
    base_data: BaseData,
):
    data = {"password": base_data["password"], "prev_password": "old pass"}
    request = domain.ChangePasswordRequest(**data)
    assert request.prev_password == "old pass"


def test_password_recovery_approve_rejects_short_password():
    data = {"email": "test@example.com", "key": "12345678-1234-1234-1234-123456789abc", "password": "weak"}
    with pytest.raises(errors.PasswordTooShortError):
        domain.PasswordRecoveryApproveRequest(**data)


def test_password_recovery_approve_rejects_insufficient_types():
    data = {"email": "test@example.com", "key": "12345678-1234-1234-1234-123456789abc", "password": "abcdefghij"}
    with pytest.raises(errors.PasswordInsufficientTypesError):
        domain.PasswordRecoveryApproveRequest(**data)


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
