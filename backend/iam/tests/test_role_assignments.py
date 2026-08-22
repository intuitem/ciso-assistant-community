from typing import Literal

from django.db import models
from django.contrib.auth.models import Permission
import pytest

from global_settings import utils as ff_utils
from global_settings.models import GlobalSettings
from global_settings.utils import clear_feature_flags_cache
from iam.models import RoleAssignment, User, UserGroup, IdPGroup, Role, Folder
from core.models import (
    AppliedControl,
    RequirementAssignment,
    FilteringLabel,
    Actor,
    Team,
)
from tprm.models import Entity

BASIC_PERMISSION_LIST = [
    "view_appliedcontrol",
    "transition_requirementassignment",
    "view_folder",
]


class Utils:
    """File(/module)-local utils."""

    @staticmethod
    def _get_global_settings() -> GlobalSettings:
        settings, _ = GlobalSettings.objects.get_or_create(
            name=GlobalSettings.Names.FEATURE_FLAGS,
            defaults={"value": {}},
        )
        return settings

    @staticmethod
    def set_idp_groups_feature_flag():
        settings = Utils._get_global_settings()
        settings.value = {
            **(settings.value or {}),
            "idp_groups": True,
        }
        settings.save(update_fields=["value"])
        # Direct ORM write: bypasses the serializer, the single invalidation
        # point of the feature-flags cache.
        clear_feature_flags_cache()

    @staticmethod
    def unset_idp_groups_feature_flag():
        settings = Utils._get_global_settings()
        settings.value = {
            **(settings.value or {}),
            "idp_groups": False,
        }
        settings.save(update_fields=["value"])
        clear_feature_flags_cache()


@pytest.fixture(autouse=True)
def _enterprise_flags(monkeypatch):
    """idp_groups is enterprise-only (declared on the EE FeatureFlagsSerializer,
    hence unsupported on CE); the IdP-group inheritance tests exercise the
    EE-gated behavior from the CE test bed."""
    supported = ff_utils.get_supported_feature_flags() | {"idp_groups"}
    monkeypatch.setattr(ff_utils, "get_supported_feature_flags", lambda: supported)


@pytest.mark.django_db
class TestRoleAssignment:
    def test_list_user_role_assignments(self):
        """Ensure `RoleAssignment.get_role_assignments_from_user` can property list the `user` role assignments."""

        Utils.set_idp_groups_feature_flag()

        user = User.objects.create_user("user@gmail.com")

        assert RoleAssignment.get_role_assignments_from_user(user).count() == 0, (
            "Newly created user MUST NOT have a role being assigned to them implicitely."
        )

        user2 = User.objects.create_user("user2@gmail.com")
        user_group2 = UserGroup.objects.create(name="user_group2")
        idp_group2 = IdPGroup.objects.create(name="idp_group2")
        user_group2.idp_groups.add(idp_group2)

        role = Role.objects.create(name="role")
        role.permissions.set(
            Permission.objects.filter(codename__in=BASIC_PERMISSION_LIST)
        )
        RoleAssignment.objects.create(user=user2, role=role, is_recursive=True)
        RoleAssignment.objects.create(
            user_group=user_group2, role=role, is_recursive=True
        )
        RoleAssignment.objects.create(
            user=user2, user_group=user_group2, role=role, is_recursive=True
        )

        assert RoleAssignment.get_role_assignments_from_user(user).count() == 0, (
            "Unrelated role assignments are incorrectly considered as being related to the `user`."
        )

        # Testing the most basic `RoleAssignment` (directly assigned to the user with `role_assignment.user=user`):

        RoleAssignment.objects.create(user=user, role=role, is_recursive=True)

        assert RoleAssignment.get_role_assignments_from_user(user).count() == 1, (
            "A role assignment is missing from the returned queryset."
        )

        user_group = UserGroup.objects.create(name="user_group")
        user.user_groups.add(user_group)

        # Testing if `RoleAssignment.user_group` works as expected:

        RoleAssignment.objects.create(
            user_group=user_group, role=role, is_recursive=True
        )
        RoleAssignment.objects.create(
            user_group=user_group, user=user, role=role, is_recursive=True
        )

        assert RoleAssignment.get_role_assignments_from_user(user).count() == 3, (
            "A role assignment is missing from the returned queryset."
        )

        # Testing if `RoleAssignment` with `role_assignment.is_recursive=False` are also detected:

        RoleAssignment.objects.create(user=user, role=role, is_recursive=False)
        RoleAssignment.objects.create(
            user_group=user_group, role=role, is_recursive=False
        )
        RoleAssignment.objects.create(
            user_group=user_group, user=user, role=role, is_recursive=False
        )

        assert RoleAssignment.get_role_assignments_from_user(user).count() == 6, (
            "A role assignment is missing from the returned queryset."
        )

        # Testing if the `idp_groups` work for `RoleAssignment`.

        idp_group = IdPGroup.objects.create(name="idp_group")
        user_group_with_idp_group = UserGroup.objects.create(
            name="user_group_with_idp_group"
        )
        user_group_with_idp_group.idp_groups.add(idp_group)

        RoleAssignment.objects.create(user_group=user_group_with_idp_group, role=role)
        user.idp_groups.add(idp_group)

        assert RoleAssignment.get_role_assignments_from_user(user).count() == 7, (
            "IdPGroup based role assignment not detected."
        )

        Utils.unset_idp_groups_feature_flag()

        assert RoleAssignment.get_role_assignments_from_user(user).count() == 6, (
            "IdPGroup based role assignment SHALL NOT be listed when the 'idp_groups' feature flag is unset."
        )

        user.is_active = False
        user.save()

        assert RoleAssignment.get_role_assignments_from_user(user).count() == 0, (
            "An inactive user shouldn't be considered to have any active role assignment."
        )

    def test_list_user_role_assignments_from_permission(self):
        user = User.objects.create_user("user@gmail.com")
        role = Role.objects.create(name="role")
        role.permissions.set(
            Permission.objects.filter(codename__in=BASIC_PERMISSION_LIST)
        )

        permission = Permission.objects.get(codename="view_appliedcontrol")

        assert (
            RoleAssignment._get_role_assignments_from_permission(
                user, permission
            ).count()
            == 0
        ), "No role assignment have been yet assigned."
        assert (
            RoleAssignment._get_role_assignments_from_permission(
                user, ("view", AppliedControl)
            ).count()
            == 0
        ), "No role assignment have been yet assigned."

        RoleAssignment.objects.create(user=user, role=role)

        assert (
            RoleAssignment._get_role_assignments_from_permission(
                user, permission
            ).count()
            == 1
        ), "Role assignment couldn't be detected."
        assert (
            RoleAssignment._get_role_assignments_from_permission(
                user, ("view", AppliedControl)
            ).count()
            == 1
        ), "Role assignment couldn't be detected."
        assert (
            RoleAssignment._get_role_assignments_from_permission(
                user, ("transition", RequirementAssignment)
            ).count()
            == 1
        ), "Role assignment couldn't be detected."

        unassigned_permission1 = Permission.objects.get(
            codename="change_appliedcontrol"
        )
        unassigned_permission2 = Permission.objects.get(codename="backup")
        unassigned_permission3 = Permission.objects.get(
            codename="view_compliance_assessment_full"
        )

        assert (
            RoleAssignment._get_role_assignments_from_permission(
                user, unassigned_permission1
            ).count()
            == 0
        ), "Role assignment wrongly considered as assigned."
        assert (
            RoleAssignment._get_role_assignments_from_permission(
                user, ("change", AppliedControl)
            ).count()
            == 0
        ), "Role assignment wrongly considered as assigned."

        assert (
            RoleAssignment._get_role_assignments_from_permission(
                user, unassigned_permission2
            ).count()
            == 0
        ), "Role assignment wrongly considered as assigned."
        assert (
            RoleAssignment._get_role_assignments_from_permission(
                user, unassigned_permission3
            ).count()
            == 0
        ), "Role assignment wrongly considered as assigned."


@pytest.mark.django_db
class TestPermissionCheck:
    type FilteringLabelPermissionPrefix = Literal["view", "change", "delete"]

    def test_inactive_user_perms(self):
        """Ensure inactive users (`User.is_active=False`) can't access anything."""

        user = User.objects.create_user("user@gmail.com")
        role = Role.objects.create(name="role")
        role.permissions.set(
            Permission.objects.filter(codename__in=BASIC_PERMISSION_LIST)
        )

        role_assignment = RoleAssignment.objects.create(user=user, role=role)
        role_assignment.perimeter_folders.add(Folder.get_root_folder())

        folder = Folder.get_root_folder()

        applied_control = AppliedControl.objects.create(
            name="applied_control", folder=folder
        )

        assert (
            RoleAssignment.is_object_accessible(
                user, "view", AppliedControl, applied_control.id
            )
            is True
        ), "This object should be accessible."
        assert (
            RoleAssignment.get_viewable_object_ids(user, AppliedControl, folder).count()
            == 1
        ), "The previously created `applied_control` should be accessible."

        user.is_active = False
        user.save()

        assert (
            RoleAssignment.is_object_accessible(
                user, "view", AppliedControl, applied_control.id
            )
            is False
        ), (
            "Inactive users shouldn't have any right (no object should be accessible to them)."
        )
        assert (
            RoleAssignment.get_viewable_object_ids(user, AppliedControl, folder).count()
            == 0
        ), "Inactive users shouldn't have access to anything."

    def test_role_assignment_recursivity(self):
        """Ensure `RoleAssignment.is_recursive` and `{model_class}.is_published` work as expected."""

        folder1 = Folder.objects.create(name="folder1")
        folder2 = Folder.objects.create(name="folder2", parent_folder=folder1)
        folder3 = Folder.objects.create(name="folder3", parent_folder=folder2)
        folder4 = Folder.objects.create(name="folder4", parent_folder=folder3)

        user = User.objects.create_user("user@gmail.com")
        role = Role.objects.create(name="role")
        role.permissions.set(
            Permission.objects.filter(codename__in=BASIC_PERMISSION_LIST)
        )

        role_assignment = RoleAssignment.objects.create(
            user=user, role=role, is_recursive=False
        )
        role_assignment.perimeter_folders.add(folder3)

        applied_control = AppliedControl.objects.create(
            name="applied_control", folder=folder3, is_published=False
        )

        assert (
            RoleAssignment.is_object_accessible(
                user, "view", AppliedControl, applied_control.id
            )
            is True
        ), "The previously created `applied_control` should be accessible."
        assert (
            RoleAssignment.get_viewable_object_ids(
                user, AppliedControl, folder3
            ).count()
            == 1
        ), "The previously created `applied_control` should be accessible."

        applied_control.folder = folder4
        applied_control.save()

        assert (
            RoleAssignment.is_object_accessible(
                user, "view", AppliedControl, applied_control.id
            )
            is False
        ), (
            "The previously created `applied_control` shouldn't be accessible (as it's in a descendant folder)."
        )
        assert (
            RoleAssignment.get_viewable_object_ids(
                user, AppliedControl, folder3
            ).count()
            == 0
        ), (
            "The previously created `applied_control` shouldn't be accessible (as it's in a descendant folder)."
        )

        role_assignment.is_recursive = True
        role_assignment.save()

        assert (
            RoleAssignment.is_object_accessible(
                user, "view", AppliedControl, applied_control.id
            )
            is True
        ), (
            "The previously created `applied_control` should be accessible due to `is_recursive=True` (as it's in a descendant folder)."
        )
        assert (
            RoleAssignment.get_viewable_object_ids(
                user, AppliedControl, folder3
            ).count()
            == 1
        ), (
            "The previously created `applied_control` should be accessible due to `is_recursive=True` (as it's in a descendant folder)."
        )

        applied_control.folder = folder2
        applied_control.save()

        assert (
            RoleAssignment.is_object_accessible(
                user, "view", AppliedControl, applied_control.id
            )
            is False
        ), (
            "The previously created `applied_control` shouldn't be accessible (as it's in a ancestor folder)."
        )
        assert (
            RoleAssignment.get_viewable_object_ids(
                user, AppliedControl, folder3
            ).count()
            == 0
        ), (
            "The previously created `applied_control` shouldn't be accessible (as it's in a ancestor folder)."
        )

        assert (
            RoleAssignment.is_object_accessible(
                user, "change", AppliedControl, applied_control.id
            )
            is False
        ), (
            "The user shouldn't have the right to change the previous created applied control (as he doesn't have the 'change_appliedcontrol' permission)."
        )
        assert (
            RoleAssignment.get_changeable_object_ids(
                user, AppliedControl, folder3
            ).count()
            == 0
        ), (
            "The user shouldn't have the right to change the previous created applied control (as he doesn't have the 'change_appliedcontrol' permission)."
        )

        applied_control.is_published = True
        applied_control.save()

        assert (
            RoleAssignment.is_object_accessible(
                user, "view", AppliedControl, applied_control.id
            )
            is True
        ), (
            "The previously created `applied_control` should be accessible due to `is_published=True` (as it's in a ancestor folder)."
        )
        assert (
            RoleAssignment.get_viewable_object_ids(
                user, AppliedControl, folder2
            ).count()
            == 1
        ), (
            "The previously created `applied_control` should be accessible due to `is_published=True` (as it's in a ancestor folder)."
        )

        assert (
            RoleAssignment.is_object_accessible(
                user, "change", AppliedControl, applied_control.id
            )
            is False
        ), (
            "The user shouldn't have the right to change the previous created applied control (as he doesn't have the 'change_appliedcontrol' permission)."
        )
        assert (
            RoleAssignment.get_changeable_object_ids(
                user, AppliedControl, folder3
            ).count()
            == 0
        ), (
            "The user shouldn't have the right to change the previous created applied control (as he doesn't have the 'change_appliedcontrol' permission)."
        )

    def test_enclave_does_not_inherit_published_objects(self):
        """
        Ensure a user whose access is scoped to an ENCLAVE `Folder` does NOT inherit the published objects of the enclave ancestors.

        Enclaves are sealed compartments for third parties (e.g. TPRM respondents) living inside a customer domain: the plain `is_published` inheritance rule MUST NOT apply to them, otherwise the third party sees every published object of the customer's domain and of the root folder.
        """

        root_folder = Folder.get_root_folder()
        domain = Folder.objects.create(name="customer_domain")
        enclave = Folder.objects.create(
            name="enclave",
            parent_folder=domain,
            content_type=Folder.ContentType.ENCLAVE,
        )

        published_in_root = AppliedControl.objects.create(
            name="published_in_root", folder=root_folder, is_published=True
        )
        published_in_domain = AppliedControl.objects.create(
            name="published_in_domain", folder=domain, is_published=True
        )
        control_in_enclave = AppliedControl.objects.create(
            name="control_in_enclave", folder=enclave, is_published=False
        )

        role = Role.objects.create(name="role")
        role.permissions.set(
            Permission.objects.filter(codename__in=BASIC_PERMISSION_LIST)
        )

        enclave_user = User.objects.create_user("enclave_user@gmail.com")
        enclave_role_assignment = RoleAssignment.objects.create(
            user=enclave_user, role=role, is_recursive=True
        )
        enclave_role_assignment.perimeter_folders.add(enclave)

        assert (
            RoleAssignment.is_object_accessible(
                enclave_user, "view", AppliedControl, control_in_enclave.id
            )
            is True
        ), "The enclave user should have access to the objects of its enclave."

        for published_control in [published_in_root, published_in_domain]:
            assert (
                RoleAssignment.is_object_accessible(
                    enclave_user, "view", AppliedControl, published_control.id
                )
                is False
            ), (
                "An enclave-scoped user MUST NOT inherit the published objects of the enclave ancestors."
            )

        enclave_user_viewable_ids = set(
            RoleAssignment.get_viewable_object_ids(enclave_user, AppliedControl)
        )
        assert enclave_user_viewable_ids == {control_in_enclave.id}, (
            "An enclave-scoped user MUST only list the objects of its enclave, not the published objects of the enclave ancestors."
        )

        # Control group: the same assignment on a non-enclave folder DOES inherit published ancestors.
        domain_user = User.objects.create_user("domain_user@gmail.com")
        domain_role_assignment = RoleAssignment.objects.create(
            user=domain_user, role=role, is_recursive=False
        )
        domain_role_assignment.perimeter_folders.add(domain)

        assert (
            RoleAssignment.is_object_accessible(
                domain_user, "view", AppliedControl, published_in_root.id
            )
            is True
        ), (
            "A domain-scoped user should still inherit the published objects of the domain ancestors."
        )
        assert published_in_root.id in set(
            RoleAssignment.get_viewable_object_ids(domain_user, AppliedControl)
        ), (
            "A domain-scoped user should still list the published objects of the domain ancestors."
        )

    def test_filtering_label_perms(self):
        """
        Ensure `FilteringLabel` follows the STANDARD folder-scoped IAM rules, with a SINGLE exception: "add".

        `FilteringLabel` objects are (through the product surface) always stored in the root folder and force-published (`PublishInRootFolderMixin`), so:

        - "view" needs NO special case: root folder labels are visible to any user holding "view_filteringlabel" on any non-ENCLAVE folder, through the normal `is_published` inheritance (and an ENCLAVE-scoped grant sees nothing).
        - "change"/"delete" need NO special case: they require the permission on the label folder (the root folder), like any other object.
        - "add" is THE single exception: holding "add_filteringlabel" on ANY folder allows creating labels (they are force-stored in the root folder, so the standard rule would wrongly require root folder access).
        """

        root_folder = Folder.get_root_folder()
        domain1 = Folder.objects.create(name="domain1")
        domain2 = Folder.objects.create(name="domain2")
        enclave = Folder.objects.create(
            name="enclave",
            parent_folder=domain1,
            content_type=Folder.ContentType.ENCLAVE,
        )

        label_in_root = FilteringLabel.objects.create(
            label="label_in_root", folder=root_folder
        )
        assert label_in_root.is_published is True, (
            "Root folder labels MUST be auto-published (`PublishInRootFolderMixin`)."
        )
        label_in_domain1 = FilteringLabel.objects.create(
            label="label_in_domain1", folder=domain1
        )
        label_in_domain2 = FilteringLabel.objects.create(
            label="label_in_domain2", folder=domain2
        )

        filtering_label_permissions = Permission.objects.filter(
            codename__in=[
                "add_filteringlabel",
                "view_filteringlabel",
                "change_filteringlabel",
                "delete_filteringlabel",
                "view_folder",
            ]
        )
        label_role = Role.objects.create(name="label_role")
        label_role.permissions.set(filtering_label_permissions)

        add_permission = Permission.objects.get(codename="add_filteringlabel")

        # A user with the label permissions on a (non-root) domain:

        domain1_user = User.objects.create_user("domain1_labels@gmail.com")
        domain1_role_assignment = RoleAssignment.objects.create(
            user=domain1_user, role=label_role, is_recursive=False
        )
        domain1_role_assignment.perimeter_folders.add(domain1)

        assert set(
            RoleAssignment.get_viewable_object_ids(domain1_user, FilteringLabel)
        ) == {label_in_root.id, label_in_domain1.id}, (
            "A domain user MUST view the root folder labels (published) and its own domain labels, but NOT the other domains labels."
        )
        assert (
            RoleAssignment.is_object_accessible(
                domain1_user, "view", FilteringLabel, label_in_root.id
            )
            is True
        ), "Root folder labels MUST be visible through the `is_published` inheritance."
        assert (
            RoleAssignment.is_object_accessible(
                domain1_user, "view", FilteringLabel, label_in_domain2.id
            )
            is False
        ), "Other domains labels MUST NOT be visible."

        assert set(
            RoleAssignment.get_changeable_object_ids(domain1_user, FilteringLabel)
        ) == {label_in_domain1.id}, (
            "A domain user MUST only be able to change its own domain labels (NOT the root folder ones)."
        )
        assert set(
            RoleAssignment.get_deletable_object_ids(domain1_user, FilteringLabel)
        ) == {label_in_domain1.id}, (
            "A domain user MUST only be able to delete its own domain labels (NOT the root folder ones)."
        )
        assert (
            RoleAssignment.is_object_accessible(
                domain1_user, "change", FilteringLabel, label_in_root.id
            )
            is False
        ), (
            "Changing a root folder label MUST require the permission on the root folder."
        )

        assert (
            RoleAssignment.is_access_allowed(
                user=domain1_user, perm=add_permission, folder=root_folder
            )
            is True
        ), (
            "The 'add' exception: holding 'add_filteringlabel' on ANY folder MUST allow creating labels."
        )

        # A user with the label permissions on the root folder:

        root_user = User.objects.create_user("root_labels@gmail.com")
        root_role_assignment = RoleAssignment.objects.create(
            user=root_user, role=label_role, is_recursive=False
        )
        root_role_assignment.perimeter_folders.add(root_folder)

        assert set(
            RoleAssignment.get_changeable_object_ids(root_user, FilteringLabel)
        ) == {label_in_root.id}, (
            "A root folder user MUST be able to change the root folder labels."
        )

        # A user with the label permissions scoped to an ENCLAVE folder:

        enclave_user = User.objects.create_user("enclave_labels@gmail.com")
        enclave_role_assignment = RoleAssignment.objects.create(
            user=enclave_user, role=label_role, is_recursive=True
        )
        enclave_role_assignment.perimeter_folders.add(enclave)

        assert (
            set(RoleAssignment.get_viewable_object_ids(enclave_user, FilteringLabel))
            == set()
        ), (
            "An ENCLAVE-scoped grant MUST NOT see any label (the `is_published` inheritance doesn't apply to enclaves)."
        )
        assert (
            RoleAssignment.is_object_accessible(
                enclave_user, "view", FilteringLabel, label_in_root.id
            )
            is False
        ), (
            "An ENCLAVE-scoped grant MUST NOT see the root folder labels (the `is_published` inheritance doesn't apply to enclaves)."
        )

        # A user WITHOUT any label permission:

        noperm_user = User.objects.create_user("noperm_labels@gmail.com")
        noperm_role = Role.objects.create(name="noperm_role")
        noperm_role.permissions.set(
            Permission.objects.filter(codename__in=BASIC_PERMISSION_LIST)
        )
        noperm_role_assignment = RoleAssignment.objects.create(
            user=noperm_user, role=noperm_role, is_recursive=False
        )
        noperm_role_assignment.perimeter_folders.add(domain1)

        assert (
            set(RoleAssignment.get_viewable_object_ids(noperm_user, FilteringLabel))
            == set()
        ), "A user without 'view_filteringlabel' MUST NOT see any label."
        assert (
            RoleAssignment.is_access_allowed(
                user=noperm_user, perm=add_permission, folder=root_folder
            )
            is False
        ), "A user without 'add_filteringlabel' MUST NOT be allowed to create labels."

    def test_permission_perms(self):
        """Ensure everyone can view permissions, but no one can change/delete them."""

        user = User.objects.create_user("user@gmail.com")

        folder = Folder.objects.create(name="folder")
        permission = Permission.objects.first()

        assert permission is not None, "No permission found in the database."

        assert (
            RoleAssignment.is_object_accessible(user, "view", Permission, permission.id)
            is True
        ), (
            "Any Permission should be viewable (even for users with no permissions (no role assigned to them))."
        )
        assert (
            RoleAssignment.get_viewable_object_ids(user, Permission, folder).count() > 0
        ), (
            "Any Permission should be viewable (even for users with no permissions (no role assigned to them))."
        )

        admin_user = User.objects.create_superuser("admin@tests.com", is_published=True)
        admin_group = UserGroup.objects.get(name="BI-UG-ADM")
        admin_user.folder = admin_group.folder
        admin_user.save()

        assert (
            RoleAssignment.is_object_accessible(
                admin_user, "change", Permission, permission.id
            )
            is False
        ), "No one should be able to change permissions (even admins)."
        assert (
            RoleAssignment.get_changeable_object_ids(
                admin_user, Permission, folder
            ).count()
            == 0
        ), "No one should be able to change permissions (even admins)."

        assert (
            RoleAssignment.is_object_accessible(
                admin_user, "delete", Permission, permission.id
            )
            is False
        ), "No one should be able to delete permissions (even admins)."
        assert (
            RoleAssignment.get_deletable_object_ids(
                admin_user, Permission, folder
            ).count()
            == 0
        ), "No one should be able to delete permissions (even admins)."

    @staticmethod
    def _check_actor_perms(
        user: User, role: Role, actor: Actor, model: type[models.Model]
    ):
        perm_prefixes: list[TestPermissionCheck.FilteringLabelPermissionPrefix] = [
            "view",
            "change",
            "delete",
        ]

        model_name = model._meta.model_name

        for perm_prefix in perm_prefixes:
            codename = f"{perm_prefix}_{model_name}"
            permission = Permission.objects.get(codename=codename)

            assert (
                RoleAssignment.is_object_accessible(user, perm_prefix, Actor, actor.id)
                is False
            ), (
                f"The user shouldn't be able to {perm_prefix!r} the previously created actor (as he doesn't have any {codename!r} permission)."
            )
            assert (
                RoleAssignment._get_accessible_ids(
                    user, perm_prefix, Actor, user.folder
                ).count()
                == 0
            ), (
                f"The user shouldn't be able to {perm_prefix!r} the previously created actor (as he doesn't have any {codename!r} permission)."
            )

            # RoleAssignment._get_accessible_ids(user, "delete", model, folder)

            role.permissions.add(permission)

            assert (
                RoleAssignment.is_object_accessible(user, perm_prefix, Actor, actor.id)
                is True
            ), (
                f"The user should be able to {perm_prefix!r} the previously created actor (as he doesn't have any {codename!r} permission)."
            )
            assert (
                RoleAssignment._get_accessible_ids(
                    user, perm_prefix, Actor, user.folder
                ).count()
                == 1
            ), (
                f"The user should be able to {perm_prefix!r} the previously created actor (as he doesn't have any {codename!r} permission)."
            )

    def test_actor_perms(self):
        folder = Folder.objects.create(name="folder")

        user = User.objects.create_user("user@gmail.com")
        user.folder = folder
        user.save()
        role = Role.objects.create(name="role")
        role.permissions.set(
            Permission.objects.filter(codename__in=BASIC_PERMISSION_LIST)
        )

        role_assignment = RoleAssignment.objects.create(
            user=user, role=role, is_recursive=True
        )
        role_assignment.perimeter_folders.add(folder)

        # The `ActorSyncMixin` creates a new `Actor` when a `User`/`Team`/`Entity` is created.
        # That's why no `Actor` is manually created via (`Actor.objects.create`) inside this test.
        actor = Actor.objects.get(user=user)
        self._check_actor_perms(user, role, actor, User)

        Actor.objects.all().delete()  # Cleanup existing actors (as `_check_actor_perms` assert based on the count of accessible actors).
        team = Team.objects.create(folder=folder)
        actor = Actor.objects.get(team=team)
        self._check_actor_perms(user, role, actor, Team)

        Actor.objects.all().delete()
        entity = Entity.objects.create(name="entity", folder=folder)
        actor = Actor.objects.get(entity=entity)
        self._check_actor_perms(user, role, actor, Entity)


@pytest.mark.django_db
class TestFocusMode:
    def test_focus_mode_listing_scope(self):
        """
        Ensure focus mode intersects the accessible folders with the focus subtree PLUS the root folder, THROUGH THE PUBLIC API (`RoleAssignment.get_allowed_folder_ids`/`RoleAssignment.get_viewable_object_ids`):

        - Focus mode MUST NEVER extend the accessible folders: the root folder stays in scope ONLY for users with a role assignment covering it (#4470 parity: corpus-level objects stay available to admins in focus mode).
        - Published root folder objects (like the `User` objects, which are always published) remain visible to everyone through the normal `is_published` inheritance (e.g. so the user pickers keep working in focus mode).
        """
        from core.context import focus_folder_id_var

        root_folder = Folder.get_root_folder()
        domain = Folder.objects.create(name="domain")

        role = Role.objects.create(name="role")
        role.permissions.set(
            Permission.objects.filter(
                codename__in=[*BASIC_PERMISSION_LIST, "view_user"]
            )
        )

        admin_user = User.objects.create_user("admin_focus@gmail.com")
        admin_role_assignment = RoleAssignment.objects.create(
            user=admin_user, role=role, is_recursive=True
        )
        admin_role_assignment.perimeter_folders.add(root_folder)

        domain_user = User.objects.create_user("domain_focus@gmail.com")
        domain_role_assignment = RoleAssignment.objects.create(
            user=domain_user, role=role, is_recursive=True
        )
        domain_role_assignment.perimeter_folders.add(domain)

        unpublished_control_in_root = AppliedControl.objects.create(
            name="unpublished_control_in_root", folder=root_folder
        )
        # `PublishInRootFolderMixin.save` forces `is_published=True` for root folder objects: unpublish directly to model an unpublished root-scoped object (like the models without this mixin can have).
        AppliedControl.objects.filter(id=unpublished_control_in_root.id).update(
            is_published=False
        )
        published_control_in_root = AppliedControl.objects.create(
            name="published_control_in_root", folder=root_folder
        )
        control_in_domain = AppliedControl.objects.create(
            name="control_in_domain", folder=domain
        )

        token = focus_folder_id_var.set(domain.id)
        try:
            admin_allowed_folder_ids = set(
                RoleAssignment.get_allowed_folder_ids(
                    admin_user, ("view", AppliedControl)
                )
            )
            assert domain.id in admin_allowed_folder_ids, (
                "The focused folder itself MUST be accessible (admin)."
            )
            assert root_folder.id in admin_allowed_folder_ids, (
                "The root folder MUST stay accessible in focus mode for a user with a role assignment covering it (#4470 parity)."
            )

            admin_viewable_ids = set(
                RoleAssignment.get_viewable_object_ids(admin_user, AppliedControl)
            )
            assert control_in_domain.id in admin_viewable_ids, (
                "The focused folder objects MUST be visible (admin)."
            )
            assert unpublished_control_in_root.id in admin_viewable_ids, (
                "Root folder objects MUST stay visible in focus mode for a user with a role assignment on the root folder (#4470 parity)."
            )

            domain_user_allowed_folder_ids = set(
                RoleAssignment.get_allowed_folder_ids(
                    domain_user, ("view", AppliedControl)
                )
            )
            assert domain.id in domain_user_allowed_folder_ids, (
                "The focused folder itself MUST be accessible (domain user)."
            )
            assert root_folder.id not in domain_user_allowed_folder_ids, (
                "The root folder focus inclusion MUST NOT grant root folder access to users without any role assignment on it."
            )

            domain_user_viewable_ids = set(
                RoleAssignment.get_viewable_object_ids(domain_user, AppliedControl)
            )
            assert control_in_domain.id in domain_user_viewable_ids, (
                "The focused folder objects MUST be visible (domain user)."
            )
            assert unpublished_control_in_root.id not in domain_user_viewable_ids, (
                "Unpublished root folder objects MUST NOT be visible to users without any role assignment on the root folder."
            )

            for user in [admin_user, domain_user]:
                viewable_ids = set(
                    RoleAssignment.get_viewable_object_ids(user, AppliedControl)
                )
                assert published_control_in_root.id in viewable_ids, (
                    f"Published root folder objects MUST remain visible in focus mode (through the `is_published` inheritance) ({user.email!r})."
                )

                viewable_user_ids = set(
                    RoleAssignment.get_viewable_object_ids(user, User)
                )
                assert {admin_user.id, domain_user.id} <= viewable_user_ids, (
                    f"`User` objects (always published, in the root folder) MUST remain visible in focus mode ({user.email!r})."
                )
        finally:
            focus_folder_id_var.reset(token)

    def test_focus_mode_point_checks(self):
        """
        Ensure the point checks (`RoleAssignment.is_access_allowed`/`RoleAssignment.is_object_accessible`) enforce the SAME focus mode scope as the listings (a point check is a membership check in the listing accessible folder set):

        - A folder outside the focus subtree is NOT accessible while a focus folder is set (even for users with a role assignment covering it).
        - The ROOT folder stays in scope for users with a role assignment covering it (#4470 parity: corpus-level operations keep working for admins in focus mode).
        - Published root folder objects stay visible in focus mode through the normal `is_published` inheritance.
        """
        from core.context import focus_folder_id_var

        root_folder = Folder.get_root_folder()
        domain1 = Folder.objects.create(name="domain1")
        domain2 = Folder.objects.create(name="domain2")

        role = Role.objects.create(name="role")
        role.permissions.set(
            Permission.objects.filter(codename__in=BASIC_PERMISSION_LIST)
        )
        view_control_permission = Permission.objects.get(codename="view_appliedcontrol")

        admin_user = User.objects.create_user("admin_point@gmail.com")
        admin_role_assignment = RoleAssignment.objects.create(
            user=admin_user, role=role, is_recursive=True
        )
        admin_role_assignment.perimeter_folders.add(root_folder)

        domain1_user = User.objects.create_user("domain1_point@gmail.com")
        domain1_role_assignment = RoleAssignment.objects.create(
            user=domain1_user, role=role, is_recursive=True
        )
        domain1_role_assignment.perimeter_folders.add(domain1)

        unpublished_control_in_root = AppliedControl.objects.create(
            name="unpublished_control_in_root", folder=root_folder
        )
        AppliedControl.objects.filter(id=unpublished_control_in_root.id).update(
            is_published=False
        )
        published_control_in_root = AppliedControl.objects.create(
            name="published_control_in_root", folder=root_folder
        )
        control_in_domain1 = AppliedControl.objects.create(
            name="control_in_domain1", folder=domain1
        )
        control_in_domain2 = AppliedControl.objects.create(
            name="control_in_domain2", folder=domain2
        )

        token = focus_folder_id_var.set(domain1.id)
        try:
            assert (
                RoleAssignment.is_access_allowed(
                    user=admin_user, perm=view_control_permission, folder=domain2
                )
                is False
            ), (
                "A folder outside the focus subtree MUST NOT be accessible while a focus folder is set."
            )
            assert (
                RoleAssignment.is_access_allowed(
                    user=admin_user, perm=view_control_permission, folder=domain1
                )
                is True
            ), "The focus subtree MUST remain accessible."
            assert (
                RoleAssignment.is_access_allowed(
                    user=admin_user, perm=view_control_permission, folder=root_folder
                )
                is True
            ), (
                "The root folder MUST stay point-accessible in focus mode for a user with a role assignment covering it (#4470 parity)."
            )
            assert (
                RoleAssignment.is_access_allowed(
                    user=domain1_user, perm=view_control_permission, folder=root_folder
                )
                is False
            ), (
                "The root folder focus inclusion MUST NOT grant root folder access to users without any role assignment on it."
            )

            assert (
                RoleAssignment.is_object_accessible(
                    admin_user, "view", AppliedControl, control_in_domain2.id
                )
                is False
            ), (
                "Objects outside the focus subtree MUST NOT be point-accessible while a focus folder is set."
            )
            assert (
                RoleAssignment.is_object_accessible(
                    admin_user, "view", AppliedControl, control_in_domain1.id
                )
                is True
            ), "The focus subtree objects MUST remain point-accessible."
            assert (
                RoleAssignment.is_object_accessible(
                    admin_user, "view", AppliedControl, unpublished_control_in_root.id
                )
                is True
            ), (
                "Root folder objects MUST stay point-accessible in focus mode for a user with a role assignment on the root folder (#4470 parity)."
            )
            assert (
                RoleAssignment.is_object_accessible(
                    domain1_user, "view", AppliedControl, unpublished_control_in_root.id
                )
                is False
            ), (
                "The root folder focus inclusion MUST NOT grant unpublished root folder objects to users without any role assignment on the root folder."
            )
            for user in [admin_user, domain1_user]:
                assert (
                    RoleAssignment.is_object_accessible(
                        user, "view", AppliedControl, published_control_in_root.id
                    )
                    is True
                ), (
                    f"Published root folder objects MUST stay visible in focus mode (through the `is_published` inheritance) ({user.email!r})."
                )
        finally:
            focus_folder_id_var.reset(token)

        assert (
            RoleAssignment.is_access_allowed(
                user=admin_user, perm=view_control_permission, folder=domain2
            )
            is True
        ), "The focus boundary MUST be lifted once the focus folder is unset."
