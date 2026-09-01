from dataclasses import dataclass

import pytest
from django.contrib.auth.models import Permission

from core.models import AppliedControl
from iam.models import Folder, RoleAssignment, User, Role
from . import utils


@pytest.fixture(autouse=True)
def _reset_root_folder_cache():
    """Reset the cached root folder at the start+end of each test (to corrupted in-memory root folder for staying corrupted between tests)."""

    Folder._CACHED_ROOT_FOLDER = None
    yield
    Folder._CACHED_ROOT_FOLDER = None


@pytest.mark.django_db
class TestRootFolder:
    """
    The root folder is the unique/single/only ancestor of ALL `Folder` (except itself of course).

    **INVARIANTS:**
    1. There MUST NOT be more than ONE root folder.
    2. The root folder MUST be considered as builtin.
    3. We SHALL NOT be able to delete the root folder.
    4. The root folder `parent_folder` SHALL be immutable (as chaging it would break the first invariant (invariant number `1`)).
    """

    @pytest.fixture
    def root_folder(self) -> Folder:
        root_folder = Folder.get_root_folder()
        assert root_folder is not None, "No root folder was found."

        return root_folder

    def test_get_root_folder(self, root_folder: Folder):
        """Ensure `Folder.get_root_folder()` return ."""

        assert root_folder.parent_folder is None, (
            "The root folder SHALL NOT contains a parent folder (as it's the root node of the folder tree)."
        )
        assert root_folder.content_type == Folder.ContentType.ROOT, (
            "The root folder SHALL have the special `ROOT` content type."
        )
        assert root_folder.builtin is True, (
            "The root folder SHALL be considered as `builtin`."
        )

    def test_root_folder_with_parent(self, root_folder: Folder):
        """Ensure the root folder can't have a `parent_domain` as the root folder MUST the root of the folder tree."""

        new_folder = Folder.objects.create(name="new_folder")

        try:
            root_folder.parent_folder = new_folder
            root_folder.save()
        except Folder.InconsistencyError:
            return

        assert root_folder.parent_folder is None, (
            "The root folder MUST keep a NULL `parent_folder`."
        )

    def test_root_folder_without_builtin(self, root_folder: Folder):
        """Ensure the root folder always have `folder.builtin` set to `True`."""

        root_folder.builtin = False
        try:
            root_folder.save()
        except Folder.InconsistencyError:
            return

        assert root_folder.builtin is True, (
            "The root folder MUST be considered as builtin."
        )

    def test_root_folder_duplicate(self, root_folder: Folder):
        """Ensure there can't be multiple root folders."""

        with pytest.raises(Folder.InconsistencyError):
            Folder.objects.create(name="ABC", content_type=Folder.ContentType.ROOT)

        assert (
            Folder.objects.filter(content_type=Folder.ContentType.ROOT).count() == 1
        ), (
            "There can't be 2 `Folder` with no `parent_folder` (there can't be more than one root folder)."
        )

    def test_delete_root_folder(self, root_folder: Folder):
        """
        Ensure we can't delete the root folder.

        The root folder SHALL never be deleted during the entire lifetime of the database.

        - Deleting the root folder so would erase all the app data (due to `CASCADE` effect).
        - It would be pointless to let anyone (including devs) do it.
        - Having an stable(never-changing) root folder PRIMARY KEY (`pk`) is a bit convenient.
        """

        try:
            root_folder.delete()
        except Folder.InconsistencyError:
            pass

        assert Folder.objects.filter(id=root_folder.id).exists(), (
            "The root folder MUST NOT be deletable."
        )


@pytest.mark.django_db
class TestFolderTreeShape:
    """
    The folder tree is the tree formed by each `folder.parent_folder` relation.

    (tree = (directed acyclic graph) AND (all node have a single parent (except the root node)))

    **INVARIANTS:**
    1. The folder tree MUST have a single root node (a single parentless node).
    2. The folder tree MUST be acyclic (not have a cycle).
    """

    def test_multiple_folder_with_null_parent_folder(self):
        """
        Ensure there can't be 2 `Folder` with a NULL `parent_folder`.

        Having 2 `Folder` with a NULL `parent_folder` would mean we could have 2 separated folder tree.
        All Folder MUST be part of the same unique folder tree.
        """

        assert Folder.objects.filter(parent_folder=None).count() == 1, (
            "There MUST be at least one root node(Folder(parentless Folder)) in the folder tree."
        )

        for content_type in Folder.ContentType:
            try:
                Folder.objects.create(name=str(content_type), parent_folder=None)
            except Folder.InconsistencyError:
                return
            except Exception as exc:
                pytest.fail(
                    f"Unexpected exception while creating parentless folder for content_type={content_type}: {exc}"
                )

            parentless_folder_count = Folder.objects.filter(parent_folder=None).count()
            assert parentless_folder_count == 1, (
                f"A newly created folder SHALL NOT be allowed to have no `parent_domain` (folder.content_type={content_type})."
            )

    def test_cycle_on_self(self):
        """Ensure there can't be a cycle (with a folder having itself as a `parent_folder`)."""

        folder = Folder.objects.create(name="folder")
        try:
            folder.parent_folder = folder
            folder.save()
        except Folder.InconsistencyError:
            return
        except Exception:
            pass

        assert folder.parent_folder != folder, (
            "A folder MUST NOT be able to have itself as its parent."
        )

    def test_cycle_on_ancestor(self):
        """Ensure there can't be a cycle (with a folder having one of its descendant as a `parent_folder`)"""

        folder1 = Folder.objects.create(name="folder1")
        folder2 = Folder.objects.create(name="folder2", parent_folder=folder1)
        folder3 = Folder.objects.create(name="folder3", parent_folder=folder2)
        folder4 = Folder.objects.create(name="folder4", parent_folder=folder3)

        try:
            folder1.parent_folder = folder4
            folder1.save()
        except Folder.InconsistencyError:
            return
        except Exception as exc:
            pytest.fail(f"Unexpected exception while creating ancestor cycle: {exc}")

        assert folder1.parent_folder != folder4, (
            "`folder4` is a descendant domain of `folder1`, therfore `folder1` MUST NOT have `folder4` as its parent (as it would create a cycle in the folder tree)."
        )


@pytest.mark.django_db
class TestFolderDescendants:
    """
    The `Folder.descendants` field is a `ManyToManyField` which MUST be perfectly consistent to the current folder tree.

    This is very important as the IAM perform decisions based on this field.

    **INVARIANT:** The `Folder.descendants` field MUST always be consistent with the current state of the `iam_folder` SQL table.
    1. `Folder.descendants` MUST remain consistent on `folder.parent_folder` change.
    2. `Folder.descendants` MUST remain consistent on `Folder` creation.
    3. `Folder.descendants` MUST remain consistent on `Folder` deletion.
    """

    def test_parent_folder_change(self):
        """Ensure the `Folder.descendants` field is correctly updated when the `folder.parent_folder` changes."""

        utils.create_folder_tree(
            [
                utils.Node(
                    "folder_1",
                    [
                        utils.Node(
                            "folder_1_1",
                            [
                                utils.Node(
                                    "folder_1_1_1",
                                    [
                                        utils.Node("folder_1_1_1_1"),
                                        utils.Node("folder_1_1_1_2"),
                                    ],
                                )
                            ],
                        ),
                        utils.Node(
                            "folder_1_2",
                            [
                                utils.Node(
                                    "folder_1_2_1", [utils.Node("folder_2_1_1_1")]
                                )
                            ],
                        ),
                    ],
                ),
            ]
        )

        folder = Folder.objects.get(name="folder_1_1_1_2")

        utils.check_folder_ancestors(
            folder,
            [
                "folder_1",
                "folder_1_1",
                "folder_1_1_1",
            ],
        )

        folder.parent_folder = Folder.objects.get(name="folder_2_1_1_1")
        folder.save()

        utils.check_folder_ancestors(
            folder,
            [
                "folder_1",
                "folder_1_2",
                "folder_1_2_1",
                "folder_2_1_1_1",
            ],
        )

    def test_folder_creation(self):
        """Ensure the `Folder.descendants` field is correctly filled(set) when a `Folder` is created."""

        utils.create_folder_tree(
            [
                utils.Node(
                    "folder_1",
                    [
                        utils.Node(
                            "folder_1_1",
                            [
                                utils.Node(
                                    "folder_1_1_1",
                                    [
                                        utils.Node("folder_1_1_1_1"),
                                    ],
                                )
                            ],
                        ),
                        utils.Node(
                            "folder_1_2",
                            [
                                utils.Node(
                                    "folder_1_2_1", [utils.Node("folder_2_1_1_1")]
                                )
                            ],
                        ),
                    ],
                ),
            ]
        )

        parent_folder = Folder.objects.get(name="folder_1_1_1_1")
        folder = Folder.objects.create(name="new_folder", parent_folder=parent_folder)

        utils.check_folder_ancestors(
            folder,
            [
                "folder_1",
                "folder_1_1",
                "folder_1_1_1",
                "folder_1_1_1_1",
            ],
        )


@pytest.mark.django_db
class TestFolderDefaultRole:
    """
    When a `Folder` `F` has a non-NULL `F.default_role`, then if a user has a `RoleAssignment` assigned to a descendant folder of `F`.
    He will be granted the permissions of the `F.default_role` `Role` on the `F` folder, example:

    - If the `A.default_role` is set to `Role(permissions=["view_appliedcontrol"])`.
    - If `root_folder <= A <= B <= C` (`C` is a child of `B`, `B` is a child of `A`, `A` is a child of `root_folder`).
    - If the `USER` `User` has a `RoleAssignment` on `C`.
    - Then the `USER` `User` will have the `"view_appliedcontrol"` permission on `A` (and will therefore be able to view all the `AppliedControl` objects in the `A` folder).
    """

    NOT_CALLED = "The `RoleAssignment._get_default_role_allowed_folder_ids` function MUST be called by the above function, as it's the safe way for IAM functions to get the accessible folder IDs from a default_role."

    CALL_COUNT = 0
    """Count how much time the `RoleAssignment._get_default_role_allowed_folder_ids` function has been called."""

    @pytest.fixture(autouse=True)
    def _monkeypatch_default_role(self):
        """Monkeypatch `RoleAssignment._get_default_role_allowed_folder_ids` to track calls during test."""
        _get_default_role_allowed_folder_ids_original = (
            RoleAssignment._get_default_role_allowed_folder_ids
        )

        def _get_default_role_allowed_folder_ids_wrapper(*args, **kwargs):
            TestFolderDefaultRole.CALL_COUNT += 1
            return _get_default_role_allowed_folder_ids_original(*args, **kwargs)

        # Monkeypatch `RoleAssignment._get_default_role_allowed_folder_ids` to increment `CALL_COUNT` each time it's called.
        RoleAssignment._get_default_role_allowed_folder_ids = (
            _get_default_role_allowed_folder_ids_wrapper
        )

        yield

        # Restore the original method
        RoleAssignment._get_default_role_allowed_folder_ids = (
            _get_default_role_allowed_folder_ids_original
        )

    @staticmethod
    def _test_and_reset_call_count() -> bool:
        """Return `true` if the `RoleAssignment._get_default_role_allowed_folder_ids` was called (and reset the `CALL_COUNT` after)."""
        call_count = TestFolderDefaultRole.CALL_COUNT
        TestFolderDefaultRole.CALL_COUNT = 0

        assert call_count > 0, (
            "The `RoleAssignment._get_default_role_allowed_folder_ids` function MUST be called by the above function, as it's the safe way for IAM functions to get the accessible folder IDs from a default_role."
        )

    @dataclass(frozen=True)
    class UserInfo:
        user: User
        folder: Folder
        parent_folder: Folder
        applied_control: AppliedControl
        default_role_permission: Permission
        user_role_permission: Permission

    @pytest.fixture
    def ctx(self) -> TestFolderDefaultRole.UserInfo:
        # Save the root folder's original default_role to restore it later
        root_folder = Folder.get_root_folder()
        original_root_default_role = root_folder.default_role

        # Temporarily remove root folder's default_role to prevent permission pollution
        root_folder.default_role = None
        root_folder.save()

        try:
            # Create a parent folder with a default_role (use create() to avoid state pollution)
            parent_folder = Folder.objects.create(
                name=f"test_default_role_parent_{id(self)}"
            )
            default_role = Role.objects.create(name=f"test_default_role_{id(self)}")
            default_role_permission = Permission.objects.get(
                codename="view_appliedcontrol"
            )
            default_role.permissions.set([default_role_permission])
            parent_folder.default_role = default_role
            parent_folder.save()

            # Create a child folder in the parent
            folder = Folder.objects.create(
                name=f"test_default_role_child_{id(self)}", parent_folder=parent_folder
            )

            # Create a user and assign them a role on the child folder
            user = User.objects.create_user(
                f"test_default_role_user_{id(self)}@gmail.com"
            )

            user_role = Role.objects.create(
                name=f"test_default_role_user_role_{id(self)}"
            )
            user_role_permission = Permission.objects.get(codename="view_asset")
            user_role.permissions.set([user_role_permission])
            role_assignment = RoleAssignment.objects.create(
                user=user, role=user_role, is_recursive=True
            )
            role_assignment.perimeter_folders.add(folder)

            # Create an AppliedControl in the parent folder
            applied_control = AppliedControl.objects.create(
                folder=parent_folder, name=f"test_default_role_control_{id(self)}"
            )

            yield TestFolderDefaultRole.UserInfo(
                user,
                folder,
                parent_folder,
                applied_control,
                default_role_permission,
                user_role_permission,
            )

            # Cleanup after test
            user.delete()
            parent_folder.delete()
            default_role.delete()
            user_role.delete()
        finally:
            # Restore root folder's original default_role
            root_folder.default_role = original_root_default_role
            root_folder.save()

    def test_get_directly_allowed_folder_ids(self, ctx: TestFolderDefaultRole.UserInfo):
        """Test that _get_directly_allowed_folder_ids calls _get_default_role_allowed_folder_ids."""

        RoleAssignment._get_directly_allowed_folder_ids(
            ctx.user, ctx.default_role_permission
        )
        self._test_and_reset_call_count()

    def test_has_permission_anywhere(self, ctx: TestFolderDefaultRole.UserInfo):
        """Test that has_permission_anywhere calls _get_default_role_allowed_folder_ids."""

        # We use the `"view_vulnerability"` permission instead as the user isn't assigned to it.
        # When a user doesn't have a permission, this IIAM function falls back to checking if any `Folder.default_role` grants it.

        unassigned_permission = Permission.objects.get(codename="view_vulnerability")
        RoleAssignment.has_permission_anywhere(ctx.user, unassigned_permission.codename)
        self._test_and_reset_call_count()

    def test_is_access_allowed(self, ctx: TestFolderDefaultRole.UserInfo):
        """Test that is_access_allowed calls _get_default_role_allowed_folder_ids."""

        RoleAssignment.is_access_allowed(
            ctx.user, ctx.default_role_permission, ctx.parent_folder
        )
        self._test_and_reset_call_count()

    def test_is_object_accessible(self, ctx: TestFolderDefaultRole.UserInfo):
        """Test that is_object_accessible calls _get_default_role_allowed_folder_ids."""
        RoleAssignment.is_object_accessible(
            ctx.user, "view", AppliedControl, ctx.applied_control.id
        )
        self._test_and_reset_call_count()

    def test_get_allowed_folder_ids(self, ctx: TestFolderDefaultRole.UserInfo):
        """Test that get_allowed_folder_ids calls _get_default_role_allowed_folder_ids."""

        RoleAssignment.get_allowed_folder_ids(ctx.user, ctx.default_role_permission)
        self._test_and_reset_call_count()

    def test_is_object_readable(self, ctx: TestFolderDefaultRole.UserInfo):
        """Test that is_object_readable calls _get_default_role_allowed_folder_ids."""

        RoleAssignment.is_object_readable(
            ctx.user, AppliedControl, ctx.applied_control.id
        )
        self._test_and_reset_call_count()

    def test_get_actor_accessible_ids_by_perm(
        self, ctx: TestFolderDefaultRole.UserInfo
    ):
        """Test that _get_actor_accessible_ids_by_perm calls _get_default_role_allowed_folder_ids."""

        RoleAssignment._get_actor_accessible_ids_by_perm(ctx.user, "view")
        self._test_and_reset_call_count()

    def test_get_accessible_ids(self, ctx: TestFolderDefaultRole.UserInfo):
        """Test that _get_accessible_ids calls _get_default_role_allowed_folder_ids."""

        RoleAssignment._get_accessible_ids(
            ctx.user, "view", AppliedControl, ctx.parent_folder
        )
        self._test_and_reset_call_count()

    def test_get_actor_accessible_ids(self, ctx: TestFolderDefaultRole.UserInfo):
        """Test that _get_actor_accessible_ids calls _get_default_role_allowed_folder_ids."""

        RoleAssignment._get_actor_accessible_ids(ctx.user)
        self._test_and_reset_call_count()

    def test_get_viewable_object_ids(self, ctx: TestFolderDefaultRole.UserInfo):
        """Test that get_viewable_object_ids calls _get_default_role_allowed_folder_ids."""

        RoleAssignment.get_viewable_object_ids(
            ctx.user, AppliedControl, ctx.parent_folder
        )
        self._test_and_reset_call_count()

    def test_get_changeable_object_ids(self, ctx: TestFolderDefaultRole.UserInfo):
        """Test that get_changeable_object_ids calls _get_default_role_allowed_folder_ids."""

        RoleAssignment.get_changeable_object_ids(
            ctx.user, AppliedControl, ctx.parent_folder
        )
        self._test_and_reset_call_count()

    def test_get_deletable_object_ids(self, ctx: TestFolderDefaultRole.UserInfo):
        """Test that get_deletable_object_ids calls _get_default_role_allowed_folder_ids."""

        RoleAssignment.get_deletable_object_ids(
            ctx.user, AppliedControl, ctx.parent_folder
        )
        self._test_and_reset_call_count()

    def test_get_permissions(self, ctx: TestFolderDefaultRole.UserInfo):
        """Test that get_permissions returns the correct permissions via default_role mechanism."""
        codename_to_perm_name_dict = RoleAssignment.get_permissions(ctx.user)

        codenames = sorted(codename_to_perm_name_dict.keys())
        expected_codenames = sorted(
            [
                ctx.default_role_permission.codename,
                ctx.user_role_permission.codename,
            ]
        )

        assert codenames == expected_codenames, (
            "Unexpected missing/unknown/extra codenames in the RoleAssignment.get_permissions return."
        )

    def test_get_default_role_allowed_folder_ids(
        self, ctx: TestFolderDefaultRole.UserInfo
    ):
        """Test that _get_default_role_allowed_folder_ids correctly identifies folders accessible via default_role."""
        assert not RoleAssignment._get_default_role_allowed_folder_ids(
            [ctx.parent_folder.id], ctx.user_role_permission
        ).exists(), (
            "The user role not permission SHALL NOT be granted by the folder.default_role"
        )
        assert not RoleAssignment._get_default_role_allowed_folder_ids(
            [ctx.folder.id], ctx.user_role_permission
        ).exists(), (
            "The user role not permission SHALL NOT be granted by the folder.default_role"
        )

        assert list(
            RoleAssignment._get_default_role_allowed_folder_ids(
                [ctx.folder.id], ctx.default_role_permission
            )
        ) == [ctx.parent_folder.id], (
            "The user default role permissions SHALL be granted by the folder.default_role"
        )

        assert not RoleAssignment._get_default_role_allowed_folder_ids(
            [ctx.parent_folder.id], ctx.default_role_permission
        ).exists(), (
            "The folder.default_role SHALL only grant the default role for RoleAssignments not descendant folders (not on itself)."
        )

        ctx.parent_folder.default_role = None
        ctx.parent_folder.save()

        assert not RoleAssignment._get_default_role_allowed_folder_ids(
            [ctx.folder.id], ctx.default_role_permission
        ).exists(), (
            "The default role permission SHALL NOT be granted if there's no folder.default_role"
        )
