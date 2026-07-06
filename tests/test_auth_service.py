import uuid

import pytest

from backend.application.auth.auth_service import AuthService
from backend.domain.enums import UserRole
from backend.domain.exceptions import (
    EmailAlreadyRegisteredError,
    InvalidCredentialsError,
    UserNotFoundError,
)
from backend.shared.security import decode_access_token
from tests.conftest import FakeUserRepository


def _build_service() -> tuple[AuthService, FakeUserRepository]:
    users = FakeUserRepository()
    return AuthService(users), users


# -- register -----------------------------------------------------------------

async def test_register_creates_a_user_with_a_hashed_password():
    service, users = _build_service()

    user = await service.register(email="Henrik@Example.com", password="securepassword123")

    assert user.id is not None
    assert user.email == "henrik@example.com"  # normalized to lowercase
    assert user.hashed_password != "securepassword123"
    assert user.role == UserRole.SALES

    stored = await users.get_by_email("henrik@example.com")
    assert stored is not None


async def test_register_accepts_full_name_and_role():
    service, _users = _build_service()

    user = await service.register(
        email="admin@example.com",
        password="securepassword123",
        full_name="Henrik",
        role=UserRole.ADMIN,
    )

    assert user.full_name == "Henrik"
    assert user.role == UserRole.ADMIN


async def test_register_rejects_duplicate_email():
    service, _users = _build_service()
    await service.register(email="user@example.com", password="securepassword123")

    with pytest.raises(EmailAlreadyRegisteredError):
        await service.register(email="user@example.com", password="anotherpassword123")


async def test_register_rejects_duplicate_email_case_insensitively():
    service, _users = _build_service()
    await service.register(email="user@example.com", password="securepassword123")

    with pytest.raises(EmailAlreadyRegisteredError):
        await service.register(email="USER@EXAMPLE.com", password="anotherpassword123")


# -- authenticate / login -------------------------------------------------------

async def test_login_succeeds_with_correct_credentials():
    service, _users = _build_service()
    await service.register(email="user@example.com", password="securepassword123")

    token = await service.login("user@example.com", "securepassword123")

    payload = decode_access_token(token)
    assert "sub" in payload


async def test_login_token_subject_matches_registered_user_id():
    service, _users = _build_service()
    user = await service.register(email="user@example.com", password="securepassword123")

    token = await service.login("user@example.com", "securepassword123")

    payload = decode_access_token(token)
    assert payload["sub"] == str(user.id)


async def test_login_fails_with_wrong_password():
    service, _users = _build_service()
    await service.register(email="user@example.com", password="securepassword123")

    with pytest.raises(InvalidCredentialsError):
        await service.login("user@example.com", "wrong-password")


async def test_login_fails_for_unknown_email():
    service, _users = _build_service()

    with pytest.raises(InvalidCredentialsError):
        await service.login("nobody@example.com", "securepassword123")


async def test_login_fails_for_deactivated_account():
    service, users = _build_service()
    user = await service.register(email="user@example.com", password="securepassword123")
    await users.deactivate(user.id)

    with pytest.raises(InvalidCredentialsError):
        await service.login("user@example.com", "securepassword123")


# -- get_current_user -----------------------------------------------------------

async def test_get_current_user_returns_the_matching_user():
    service, _users = _build_service()
    user = await service.register(email="user@example.com", password="securepassword123")

    current = await service.get_current_user(user.id)

    assert current.id == user.id
    assert current.email == "user@example.com"


async def test_get_current_user_raises_for_unknown_id():
    service, _users = _build_service()

    with pytest.raises(UserNotFoundError):
        await service.get_current_user(uuid.uuid4())
