from typing import Literal

from django.db import models
from django.contrib.auth.models import Permission
import pytest

from global_settings.models import GlobalSettings
from iam.models import RoleAssignment, User, UserGroup, IdPGroup, Role, Folder
from core.models import (
    AppliedControl,
    RequirementAssignment,
    FilteringLabel,
    Actor,
    Team,
)
from tprm.models import Entity
from . import utils

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

    @staticmethod
    def unset_idp_groups_feature_flag():
        settings = Utils._get_global_settings()
        settings.value = {
            **(settings.value or {}),
            "idp_groups": False,
        }
        settings.save(update_fields=["value"])


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
        Ensure any permission on the `FilteringLabel` model result in having this permission globally.

        (e.g. Having the "change_filteringlabel" permission on any `Folder` should allow the user to "change" any `FilteringLabel` in the app (no matter its folder (`filtering_label.folder`))).
        """

        root_folder = Folder.get_root_folder()
        folder1 = Folder.objects.create(name="folder1")
        folder2 = Folder.objects.create(name="folder2")

        user = User.objects.create_user("user@gmail.com")
        role = Role.objects.create(name="role")
        role.permissions.set(
            Permission.objects.filter(codename__in=BASIC_PERMISSION_LIST)
        )

        role_assignment = RoleAssignment.objects.create(
            user=user, role=role, is_recursive=False
        )
        role_assignment.perimeter_folders.add(folder1)

        filtering_label0 = FilteringLabel.objects.create(
            label="filtering_label1", folder=root_folder
        )
        filtering_label1 = FilteringLabel.objects.create(
            label="filtering_label2", folder=folder1
        )
        filtering_label2 = FilteringLabel.objects.create(
            label="filtering_label3", folder=folder2
        )

        total_filtering_label_count = FilteringLabel.objects.count()

        perm_prefixes: list[TestPermissionCheck.FilteringLabelPermissionPrefix] = [
            "view",
            "change",
            "delete",
        ]

        for perm_prefix in perm_prefixes:
            assert (
                RoleAssignment.is_object_accessible(
                    user, perm_prefix, FilteringLabel, filtering_label0.id
                )
                is False
            ), "The user doesn't have any permission on the FilteringLabel model yet."
            assert (
                RoleAssignment._get_accessible_ids(
                    user, perm_prefix, FilteringLabel, folder1
                ).count()
                == 0
            ), "The user doesn't have any permission on the FilteringLabel model yet."

        for perm_prefix in perm_prefixes:
            role.permissions.add(
                Permission.objects.get(codename=f"{perm_prefix}_filteringlabel")
            )

            for filtering_label in [
                filtering_label0,
                filtering_label1,
                filtering_label2,
            ]:
                is_filtering_label_accessible = (
                    RoleAssignment.is_object_accessible(
                        user, "view", FilteringLabel, filtering_label.id
                    )
                    is True
                )

                assert is_filtering_label_accessible, (
                    f"The user should be able to {perm_prefix!r} the previously created FilteringLabel (in folder {filtering_label.folder.name!r})."
                )

                accessible_filtering_label_count = RoleAssignment._get_accessible_ids(
                    user, perm_prefix, FilteringLabel, filtering_label.folder
                ).count()

                assert (
                    accessible_filtering_label_count == total_filtering_label_count
                ), (
                    f"The user should be able to {perm_prefix!r} the previously created FilteringLabel (in folder {filtering_label.folder.name!r})."
                )

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
    def test_focus_accessible_folder_ids(self):
        """Ensure the `RoleAssignment._get_focus_accessible_folder_ids` function returns the proper accessible folders IDs."""

        utils.create_folder_tree(
            [
                utils.Node(
                    name="folder_1",
                    children=[
                        utils.Node(
                            name="folder_1_1",
                            children=[
                                utils.Node(name="folder_1_1_1"),
                                utils.Node(
                                    name="folder_1_1_2",
                                    children=[
                                        utils.Node(name="folder_1_1_2_1"),
                                        utils.Node(name="folder_1_1_2_2"),
                                    ],
                                ),
                            ],
                        ),
                        utils.Node(
                            name="folder_1_2",
                            children=[utils.Node(name="folder_1_2_1")],
                        ),
                    ],
                )
            ]
        )

        folder_name_set = set(Folder.objects.values_list("name", flat=True))

        root_folder = Folder.get_root_folder()
        assert root_folder is not None, "Root folder not found."

        all_folder_ids = Folder.objects.all().values_list("id", flat=True)
        focused_folder_ids = RoleAssignment._get_focus_accessible_folder_ids(
            root_folder.id, all_folder_ids
        )

        assert focused_folder_ids.count() == Folder.objects.count(), (
            "All folders SHALL be accessible (when the focus folder is the root folder)."
        )

        focus_folder = Folder.objects.get(name="folder_1_1")
        focused_folder_ids = RoleAssignment._get_focus_accessible_folder_ids(
            focus_folder.id, all_folder_ids
        )

        folder_name_set.difference_update(
            [
                root_folder.name,
                "folder_1",
                "folder_1_2",
                "folder_1_2_1",
            ]
        )

        focused_folder_names = Folder.objects.filter(
            id__in=focused_folder_ids
        ).values_list("name", flat=True)

        assert sorted(focused_folder_names) == sorted(folder_name_set), (
            "Unexpected/missing focused folders."
        )

        focus_folder = Folder.objects.get(name="folder_1_1_2_2")

        focused_folder_ids = RoleAssignment._get_focus_accessible_folder_ids(
            focus_folder.id, all_folder_ids
        )

        assert list(focused_folder_ids) == [focus_folder.id], (
            "Focusing on a folder with no children SHALL make it the only accessible one."
        )

    def test_filter_accessible_folder_ids_by_focus_folder(self):
        """Ensure the `RoleAssignment._filter_accessible_folder_ids_by_focus_folder` returns the proper accessible folder IDs."""

        utils.create_folder_tree(
            [
                utils.Node(
                    name="folder_1",
                    children=[
                        utils.Node(
                            name="folder_1_1",
                            children=[
                                utils.Node(
                                    name="folder_1_1_1",
                                    children=[
                                        utils.Node(name="folder_1_1_1_1"),
                                        utils.Node(name="folder_1_1_1_2"),
                                    ],
                                ),
                                utils.Node(name="folder_1_1_2"),
                            ],
                        ),
                        utils.Node(
                            name="folder_1_2",
                            children=[
                                utils.Node(
                                    name="folder_1_2_1",
                                    children=[
                                        utils.Node(name="folder_1_2_1_1"),
                                    ],
                                ),
                                utils.Node(name="folder_1_2_2"),
                            ],
                        ),
                        utils.Node(name="folder_1_3"),
                    ],
                ),
                utils.Node(
                    name="folder_2",
                    children=[
                        utils.Node(name="folder_2_1"),
                        utils.Node(name="folder_2_2"),
                    ],
                ),
            ]
        )

        focus_folder = Folder.objects.get(name="folder_1_1")

        accessible_folder_ids = (
            RoleAssignment._filter_accessible_folder_ids_by_focus_folder(
                focus_folder, [focus_folder.id], []
            )
        )
        assert list(accessible_folder_ids) == [focus_folder.id], (
            "The focused folder should be the only accessible one (as there's no recursive folder)."
        )

        accessible_folder_ids = (
            RoleAssignment._filter_accessible_folder_ids_by_focus_folder(
                focus_folder, [], [focus_folder.id]
            )
        )
        assert focus_folder.id in accessible_folder_ids, (
            "The focused folder SHALL always be accessible."
        )

        accessible_folder_ids = (
            RoleAssignment._filter_accessible_folder_ids_by_focus_folder(
                focus_folder, [focus_folder.id], [focus_folder.id]
            )
        )
        assert focus_folder.id in accessible_folder_ids, (
            "The focused folder SHALL always be accessible."
        )

        focus_descendant = Folder.objects.get(name="folder_1_1_1_1")

        accessible_folder_ids = (
            RoleAssignment._filter_accessible_folder_ids_by_focus_folder(
                focus_folder, [focus_descendant.id], []
            )
        )
        assert list(accessible_folder_ids) == [focus_descendant.id], (
            "The descendant folder should be the only accessible one (as there's no recursive folder)."
        )

        accessible_folder_ids = (
            RoleAssignment._filter_accessible_folder_ids_by_focus_folder(
                focus_folder, [], [focus_descendant.id]
            )
        )
        assert focus_descendant.id in accessible_folder_ids, (
            "A descendant folder of the focused folder SHALL be accessible."
        )

        accessible_folder_ids = (
            RoleAssignment._filter_accessible_folder_ids_by_focus_folder(
                focus_folder, [focus_descendant.id], [focus_descendant.id]
            )
        )
        assert focus_descendant.id in accessible_folder_ids, (
            "A descendant folder of the focused folder SHALL be accessible."
        )

        focus_ancestor = focus_folder.parent_folder.parent_folder

        root_folder = Folder.get_root_folder()

        assert root_folder is not None, "Root folder not found."

        all_focused_folder_ids = (
            RoleAssignment._filter_accessible_folder_ids_by_focus_folder(
                focus_folder, [], [root_folder.id]
            )
        )
        accessible_folder_ids = (
            RoleAssignment._filter_accessible_folder_ids_by_focus_folder(
                focus_folder, [], [focus_ancestor.id]
            )
        )

        assert all_focused_folder_ids.count() > 0, (
            "Having a recursive role assignment over the root folder SHALL make at least one folder being accessible."
        )
        assert sorted(accessible_folder_ids) == sorted(all_focused_folder_ids), (
            "Having a recursive role assignment on an ancestor folder of the focused folder SHALL make all the descendant of the focused folder accessible."
        )

        accessible_folder_ids = (
            RoleAssignment._filter_accessible_folder_ids_by_focus_folder(
                focus_folder, [focus_ancestor.id], [focus_ancestor.id]
            )
        )
        assert sorted(accessible_folder_ids) == sorted(all_focused_folder_ids), (
            "Having a recursive role assignment on an ancestor folder of the focused folder SHALL make all the descendant of the focused folder accessible."
        )

        accessible_folder_ids = (
            RoleAssignment._filter_accessible_folder_ids_by_focus_folder(
                focus_folder, [focus_ancestor.id], []
            )
        )
        assert accessible_folder_ids.count() == 0, (
            "An ancestor folder of the focused folder SHALL NOT be accessible."
        )

        ancestor_folder_ids = focus_folder.get_parent_folders().values_list(
            "id", flat=True
        )
        unrelated_folder_ids = [
            Folder.objects.get(name=folder_name).id
            for folder_name in [
                "folder_1_2",
                "folder_1_2_1",
                "folder_1_2_1_1",
                "folder_1_2_2",
                "folder_1_3",
            ]
        ]

        accessible_folder_ids = (
            RoleAssignment._filter_accessible_folder_ids_by_focus_folder(
                focus_folder,
                [*ancestor_folder_ids, *unrelated_folder_ids],
                unrelated_folder_ids,
            )
        )

        assert accessible_folder_ids.count() == 0, (
            "Role assignments on an unrelated the focused folder (being nor an ancestor folder, nor in the the focused folder subtree) SHALL not make anything accessible."
        )

        focus_folder = Folder.objects.get(name="folder_1")

        non_recursive_folder_ids = [Folder.objects.get(name="folder_1_3").id]
        recursive_folder_ids = [
            Folder.objects.get(name=folder_name).id
            for folder_name in [
                "folder_1_1_1",
                "folder_1_2_1",
                "folder_1_1_2",
            ]
        ]

        accessible_folder_ids = (
            RoleAssignment._filter_accessible_folder_ids_by_focus_folder(
                focus_folder,
                non_recursive_folder_ids,
                recursive_folder_ids,
            )
        )

        expected_accessible_folder_ids = [
            Folder.objects.get(name=folder_name).id
            for folder_name in [
                "folder_1_3",
                "folder_1_1_1",
                "folder_1_1_1_1",
                "folder_1_1_1_2",
                "folder_1_2_1",
                "folder_1_2_1_1",
                "folder_1_1_2",
            ]
        ]

        assert sorted(accessible_folder_ids) == sorted(
            expected_accessible_folder_ids
        ), "Unexpected accessible folder IDs."

        accessible_folder_ids2 = (
            RoleAssignment._filter_accessible_folder_ids_by_focus_folder(
                focus_folder,
                [*non_recursive_folder_ids, root_folder.id],
                recursive_folder_ids,
            )
        )

        assert sorted(accessible_folder_ids) == sorted(accessible_folder_ids2), (
            "A non-recursive root folder access SHALL NOT make any extra folder accessible (except if the focused folder is also the root folder itself)."
        )
