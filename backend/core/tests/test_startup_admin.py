import pytest
from django.test import override_settings

from core.startup import ensure_admin_user
from iam.models import Folder, User, UserGroup


@pytest.fixture
def administrators():
    return UserGroup.objects.get(name="BI-UG-ADM", folder=Folder.get_root_folder())


pytestmark = [
    pytest.mark.django_db,
    pytest.mark.usefixtures("administrators"),
]


@override_settings(
    CISO_ASSISTANT_SUPERUSER_EMAIL="new@test.com",
    FORCE_CREATE_ADMIN=False,
    EMAIL_HOST=None,
    EMAIL_HOST_RESCUE=None,
)
def test_create_superuser_when_admin_group_empty(administrators):
    """First boot: no admins, email set, user doesn't exist -> create."""
    administrators.user_set.clear()

    ensure_admin_user()

    user = User.objects.get(email="new@test.com")
    assert user.is_superuser
    assert administrators in user.user_groups.all()


@override_settings(
    CISO_ASSISTANT_SUPERUSER_EMAIL="other@test.com",
    FORCE_CREATE_ADMIN=False,
    EMAIL_HOST=None,
    EMAIL_HOST_RESCUE=None,
)
def test_no_create_when_admin_group_not_empty_and_no_force(administrators):
    """Admin group has members, no FORCE -> nothing happens."""
    existing = User.objects.create_superuser(
        email="existing@test.com", is_superuser=True
    )
    existing.user_groups.add(administrators)

    ensure_admin_user()

    assert not User.objects.filter(email="other@test.com").exists()


@override_settings(
    CISO_ASSISTANT_SUPERUSER_EMAIL="forced@test.com",
    FORCE_CREATE_ADMIN=True,
    EMAIL_HOST=None,
    EMAIL_HOST_RESCUE=None,
)
def test_force_create_new_user(administrators):
    """FORCE_CREATE_ADMIN + email set + user doesn't exist -> create."""
    ensure_admin_user()

    user = User.objects.get(email="forced@test.com")
    assert user.is_superuser
    assert administrators in user.user_groups.all()


@override_settings(
    CISO_ASSISTANT_SUPERUSER_EMAIL="regular@test.com",
    FORCE_CREATE_ADMIN=True,
    EMAIL_HOST=None,
    EMAIL_HOST_RESCUE=None,
)
def test_force_promote_existing_user(administrators):
    """FORCE_CREATE_ADMIN + user exists but not superuser -> promote."""
    user = User.objects.create(email="regular@test.com", is_superuser=False)

    ensure_admin_user()

    user.refresh_from_db()
    assert user.is_superuser
    assert administrators in user.user_groups.all()


@override_settings(
    CISO_ASSISTANT_SUPERUSER_EMAIL="regular@test.com",
    FORCE_CREATE_ADMIN=False,
    EMAIL_HOST=None,
    EMAIL_HOST_RESCUE=None,
)
def test_no_promote_without_force(administrators):
    """Existing user, admin group empty, no FORCE -> don't promote."""
    administrators.user_set.clear()
    user = User.objects.create(email="regular@test.com", is_superuser=False)

    ensure_admin_user()

    user.refresh_from_db()
    assert not user.is_superuser
    assert administrators not in user.user_groups.all()


@override_settings(
    CISO_ASSISTANT_SUPERUSER_EMAIL=None,
    FORCE_CREATE_ADMIN=True,
    EMAIL_HOST=None,
    EMAIL_HOST_RESCUE=None,
)
def test_no_email_does_nothing(administrators):
    """No CISO_ASSISTANT_SUPERUSER_EMAIL -> no user created."""
    administrators.user_set.clear()
    count_before = User.objects.count()

    ensure_admin_user()

    assert User.objects.count() == count_before


@override_settings(
    CISO_ASSISTANT_SUPERUSER_EMAIL="super@test.com",
    FORCE_CREATE_ADMIN=True,
    EMAIL_HOST=None,
    EMAIL_HOST_RESCUE=None,
)
def test_already_superuser_stays_in_group(administrators):
    """User already superuser -> just ensure they're in admin group."""
    user = User.objects.create_superuser(email="super@test.com", is_superuser=True)

    ensure_admin_user()

    user.refresh_from_db()
    assert user.is_superuser
    assert administrators in user.user_groups.all()


@override_settings(
    CISO_ASSISTANT_SUPERUSER_EMAIL="inactive@test.com",
    FORCE_CREATE_ADMIN=True,
    EMAIL_HOST=None,
    EMAIL_HOST_RESCUE=None,
)
def test_force_promote_inactive_user_reactivates(administrators):
    """FORCE_CREATE_ADMIN + inactive user -> promote and reactivate."""
    user = User.objects.create(
        email="inactive@test.com", is_superuser=False, is_active=False
    )

    ensure_admin_user()

    user.refresh_from_db()
    assert user.is_superuser
    assert user.is_active
    assert administrators in user.user_groups.all()
