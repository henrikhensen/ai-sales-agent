"""Unit tests for the role-based-access-control dependency functions.

These call the dependency functions directly with plain ``User`` instances
— no HTTP layer, no database — since they are pure authorization checks.
"""

import uuid

import pytest
from fastapi import HTTPException

from backend.api.dependencies.auth import (
    require_active_user,
    require_admin_user,
    require_reviewer_or_admin,
    require_roles,
    require_sales_or_admin,
    require_sales_reviewer_or_admin,
)
from backend.domain.entities.user import User
from backend.domain.enums import UserRole


def _user(role: UserRole, is_active: bool = True, is_superuser: bool = False) -> User:
    return User(
        id=uuid.uuid4(),
        email=f"{role.value}@example.com",
        hashed_password="hashed-value",
        role=role,
        is_active=is_active,
        is_superuser=is_superuser,
    )


# -- require_active_user -------------------------------------------------------

async def test_require_active_user_allows_active_account():
    user = _user(UserRole.SALES, is_active=True)
    assert await require_active_user(user) is user


async def test_require_active_user_blocks_inactive_account():
    user = _user(UserRole.SALES, is_active=False)
    with pytest.raises(HTTPException) as exc_info:
        await require_active_user(user)
    assert exc_info.value.status_code == 403


# -- require_admin_user ---------------------------------------------------------

async def test_require_admin_user_allows_admin():
    user = _user(UserRole.ADMIN)
    assert await require_admin_user(user) is user


async def test_require_admin_user_allows_superuser_regardless_of_role():
    user = _user(UserRole.SALES, is_superuser=True)
    assert await require_admin_user(user) is user


async def test_require_admin_user_blocks_sales():
    user = _user(UserRole.SALES)
    with pytest.raises(HTTPException) as exc_info:
        await require_admin_user(user)
    assert exc_info.value.status_code == 403


async def test_require_admin_user_blocks_reviewer():
    user = _user(UserRole.REVIEWER)
    with pytest.raises(HTTPException) as exc_info:
        await require_admin_user(user)
    assert exc_info.value.status_code == 403


# -- require_roles ---------------------------------------------------------------

async def test_require_roles_allows_a_listed_role():
    check = require_roles(UserRole.REVIEWER, UserRole.SALES)
    user = _user(UserRole.REVIEWER)
    assert await check(user) is user


async def test_require_roles_blocks_an_unlisted_role():
    check = require_roles(UserRole.REVIEWER, UserRole.SALES)
    user = _user(UserRole.ADMIN)
    with pytest.raises(HTTPException) as exc_info:
        await check(user)
    assert exc_info.value.status_code == 403


async def test_require_roles_allows_superuser_even_if_role_not_listed():
    check = require_roles(UserRole.REVIEWER)
    user = _user(UserRole.SALES, is_superuser=True)
    assert await check(user) is user


# -- require_reviewer_or_admin ----------------------------------------------------

async def test_require_reviewer_or_admin_allows_reviewer():
    user = _user(UserRole.REVIEWER)
    assert await require_reviewer_or_admin(user) is user


async def test_require_reviewer_or_admin_allows_admin():
    user = _user(UserRole.ADMIN)
    assert await require_reviewer_or_admin(user) is user


async def test_require_reviewer_or_admin_blocks_sales():
    user = _user(UserRole.SALES)
    with pytest.raises(HTTPException) as exc_info:
        await require_reviewer_or_admin(user)
    assert exc_info.value.status_code == 403


# -- require_sales_or_admin -------------------------------------------------------

async def test_require_sales_or_admin_allows_sales():
    user = _user(UserRole.SALES)
    assert await require_sales_or_admin(user) is user


async def test_require_sales_or_admin_allows_admin():
    user = _user(UserRole.ADMIN)
    assert await require_sales_or_admin(user) is user


async def test_require_sales_or_admin_blocks_reviewer():
    user = _user(UserRole.REVIEWER)
    with pytest.raises(HTTPException) as exc_info:
        await require_sales_or_admin(user)
    assert exc_info.value.status_code == 403


# -- require_sales_reviewer_or_admin ----------------------------------------------

@pytest.mark.parametrize("role", [UserRole.ADMIN, UserRole.REVIEWER, UserRole.SALES])
async def test_require_sales_reviewer_or_admin_allows_every_known_role(role):
    user = _user(role)
    assert await require_sales_reviewer_or_admin(user) is user
