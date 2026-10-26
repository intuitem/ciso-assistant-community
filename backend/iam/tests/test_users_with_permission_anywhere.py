"""RoleAssignment.users_with_permission_anywhere is the batch form of
has_permission_anywhere: both must agree on every grant source."""

import pytest
from django.contrib.auth.models import Permission

from core.startup import startup
from iam.models import Folder, IdPGroup, Role, RoleAssignment, User, UserGroup

GRANTED = "add_asset"


def _role(name, codenames):
    role = Role.objects.create(name=name)
    role.permissions.set(Permission.objects.filter(codename__in=codenames))
    return role


def _assign(role, folder, *, user=None, user_group=None):
    assignment = RoleAssignment.objects.create(
        role=role, user=user, user_group=user_group, folder=folder, is_recursive=True
    )
    assignment.perimeter_folders.add(folder)


def _member(email, group, **extra):
    user = User.objects.create_user(email=email, **extra)
    group.user_set.add(user)
    return user


@pytest.fixture
def grants(db):
    """One user per way of holding GRANTED, and look-alikes that must not."""
    startup(sender=None, **{})
    root = Folder.get_root_folder()
    granting = _role("granting", [GRANTED])
    neutral = _role("neutral", ["view_folder"])

    # The default role is the only grant source on this domain's subtree.
    domain = Folder.objects.create(
        name="domain",
        parent_folder=root,
        content_type=Folder.ContentType.DOMAIN,
        default_role=granting,
    )
    subdomain = Folder.objects.create(
        name="subdomain", parent_folder=domain, content_type=Folder.ContentType.DOMAIN
    )
    enclave = Folder.objects.create(
        name="enclave", parent_folder=domain, content_type=Folder.ContentType.ENCLAVE
    )

    def builtin_group(name, folder):
        group = UserGroup.objects.create(name=name, folder=folder, builtin=True)
        _assign(neutral, folder, user_group=group)
        return group

    on_domain = builtin_group("on domain", domain)
    on_subdomain = builtin_group("on subdomain", subdomain)
    on_enclave = builtin_group("on enclave", enclave)
    custom = UserGroup.objects.create(name="custom", folder=domain)
    _assign(neutral, domain, user_group=custom)
    granting_group = UserGroup.objects.create(name="granting", folder=root)
    _assign(granting, root, user_group=granting_group)
    idp_group = IdPGroup.objects.create(name="idp")
    idp_group.user_groups.add(granting_group)

    direct = User.objects.create_user("direct@tests.com")
    _assign(granting, root, user=direct)
    idp_member = User.objects.create_user("idp@tests.com")
    idp_member.idp_groups.add(idp_group)

    return {
        "holders": {
            direct,
            _member("group@tests.com", granting_group),
            _member("default@tests.com", on_domain),
            _member("default-below@tests.com", on_subdomain),
        },
        "idp_member": idp_member,
        "others": {
            _member("inactive@tests.com", granting_group, is_active=False),
            _member("enclave@tests.com", on_enclave),
            _member("third-party@tests.com", on_domain, is_third_party=True),
            _member("custom-group@tests.com", custom),
            User.objects.create_user("nobody@tests.com"),
        },
    }


def _batch(codename):
    return set(
        RoleAssignment.users_with_permission_anywhere(
            Permission.objects.filter(codename=codename)
        )
    )


def _one_by_one(codename):
    return {
        user
        for user in User.objects.all()
        if RoleAssignment.has_permission_anywhere(user, codename)
    }


@pytest.mark.django_db
class TestUsersWithPermissionAnywhere:
    def test_every_grant_source(self, grants):
        assert _batch(GRANTED) == grants["holders"]

    def test_idp_groups_grant_only_when_inherited(self, grants, monkeypatch):
        monkeypatch.setattr(
            "global_settings.utils.idp_group_role_inheritance_enabled", lambda: True
        )

        assert _batch(GRANTED) == grants["holders"] | {grants["idp_member"]}

    @pytest.mark.parametrize(
        "codename", [GRANTED, "view_folder", "approve_riskacceptance"]
    )
    def test_agrees_with_the_per_user_check(self, grants, codename):
        assert _batch(codename) == _one_by_one(codename)

    def test_approver_filter(self, grants):
        from core.views import UserFilter

        approver = User.objects.create_user("approver@tests.com")
        approving = _role("approving", ["approve_riskacceptance"])
        _assign(approving, Folder.get_root_folder(), user=approver)

        def filtered(value):
            return set(
                UserFilter(data={"is_approver": value}, queryset=User.objects.all()).qs
            )

        assert filtered("true") == {approver}
        assert filtered("false") == set(User.objects.exclude(id=approver.id))
