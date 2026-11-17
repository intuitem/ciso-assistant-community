import pytest

from iam.models import ConnectionProfile


@pytest.mark.django_db
def test_startup_creates_one_builtin_profile_per_combination():
    profiles = sorted(ConnectionProfile.objects.all(), key=lambda p: p.rank)
    assert [(p.name, p.actions) for p in profiles] == [
        ("Read only", ["read"]),
        ("Read and create", ["read", "create"]),
        ("Read and update", ["read", "update"]),
        ("Read and delete", ["read", "delete"]),
        ("Read, create and update", ["read", "create", "update"]),
        ("Read, create and delete", ["read", "create", "delete"]),
        ("Read, update and delete", ["read", "update", "delete"]),
        ("Read, create, update and delete", ["read", "create", "update", "delete"]),
    ]
    assert all(p.builtin for p in profiles)
    assert ConnectionProfile.default().name == "Read only"
