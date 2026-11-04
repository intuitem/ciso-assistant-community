import pytest

from iam.models import ConnectionProfile


@pytest.mark.django_db
def test_startup_creates_the_four_builtin_profiles():
    profiles = sorted(ConnectionProfile.objects.all(), key=lambda p: p.rank)
    assert [(p.name, p.actions, p.builtin) for p in profiles] == [
        ("Read only", ["read"], True),
        ("Read and create", ["read", "create"], True),
        ("Read and update", ["read", "update"], True),
        ("Read, create and update", ["read", "create", "update"], True),
    ]
    assert ConnectionProfile.default().name == "Read only"
