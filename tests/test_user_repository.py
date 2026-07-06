from backend.domain.entities.user import User
from backend.domain.enums import UserRole
from tests.conftest import FakeUserRepository


async def test_create_persists_user_and_generates_id():
    repo = FakeUserRepository()

    user = await repo.create(
        User(email="user@example.com", hashed_password="hashed-value")
    )

    assert user.id is not None
    assert user.created_at is not None
    assert user.email == "user@example.com"
    assert user.role == UserRole.SALES
    assert user.is_active is True
    assert user.is_superuser is False


async def test_get_by_email_finds_the_matching_user():
    repo = FakeUserRepository()
    await repo.create(User(email="user@example.com", hashed_password="hashed-value"))

    found = await repo.get_by_email("user@example.com")

    assert found is not None
    assert found.email == "user@example.com"


async def test_get_by_email_returns_none_for_unknown_email():
    repo = FakeUserRepository()
    assert await repo.get_by_email("nobody@example.com") is None


async def test_get_by_id_returns_none_for_unknown_id():
    import uuid

    repo = FakeUserRepository()
    assert await repo.get_by_id(uuid.uuid4()) is None


async def test_deactivate_sets_is_active_false():
    repo = FakeUserRepository()
    user = await repo.create(User(email="user@example.com", hashed_password="hashed-value"))

    deactivated = await repo.deactivate(user.id)

    assert deactivated.is_active is False
    stored = await repo.get_by_id(user.id)
    assert stored.is_active is False


async def test_list_returns_all_created_users_newest_first():
    repo = FakeUserRepository()
    await repo.create(User(email="first@example.com", hashed_password="hashed-value"))
    await repo.create(User(email="second@example.com", hashed_password="hashed-value"))

    users = await repo.list()

    assert len(users) == 2
    emails = {user.email for user in users}
    assert emails == {"first@example.com", "second@example.com"}
