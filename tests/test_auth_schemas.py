import pytest
from pydantic import ValidationError

from backend.api.v1.schemas.auth import (
    LoginRequest,
    TokenResponse,
    UserCreate,
    UserRead,
)
from backend.domain.enums import UserRole


# -- UserCreate ---------------------------------------------------------------

def test_user_create_accepts_minimal_valid_input():
    user = UserCreate(email="user@example.com", password="securepassword123")
    assert user.email == "user@example.com"
    assert user.role == UserRole.SALES


def test_user_create_accepts_full_valid_input():
    user = UserCreate(
        email="henrik@example.com",
        password="securepassword123",
        full_name="Henrik",
        role="admin",
    )
    assert user.full_name == "Henrik"
    assert user.role == UserRole.ADMIN


def test_user_create_rejects_invalid_email():
    with pytest.raises(ValidationError):
        UserCreate(email="not-an-email", password="securepassword123")


def test_user_create_rejects_password_under_minimum_length():
    with pytest.raises(ValidationError):
        UserCreate(email="user@example.com", password="short")


def test_user_create_rejects_whitespace_only_full_name():
    with pytest.raises(ValidationError):
        UserCreate(email="user@example.com", password="securepassword123", full_name="   ")


def test_user_create_trims_full_name():
    user = UserCreate(
        email="user@example.com", password="securepassword123", full_name="  Henrik  "
    )
    assert user.full_name == "Henrik"


def test_user_create_rejects_unknown_role():
    with pytest.raises(ValidationError):
        UserCreate(email="user@example.com", password="securepassword123", role="superadmin")


@pytest.mark.parametrize("role", ["admin", "reviewer", "sales"])
def test_user_create_accepts_all_allowed_roles(role):
    user = UserCreate(email="user@example.com", password="securepassword123", role=role)
    assert user.role.value == role


# -- LoginRequest --------------------------------------------------------------

def test_login_request_requires_email_and_password():
    with pytest.raises(ValidationError):
        LoginRequest(email="user@example.com")


def test_login_request_rejects_invalid_email():
    with pytest.raises(ValidationError):
        LoginRequest(email="not-an-email", password="securepassword123")


# -- UserRead / TokenResponse --------------------------------------------------

def test_user_read_requires_all_account_fields():
    with pytest.raises(ValidationError):
        UserRead(email="user@example.com")


def test_token_response_defaults_token_type_to_bearer():
    response = TokenResponse(access_token="abc.def.ghi")
    assert response.token_type == "bearer"
