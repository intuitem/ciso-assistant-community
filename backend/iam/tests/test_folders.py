from dataclasses import dataclass, field
from typing import Optional

import pytest

from iam.models import Folder

"""
@pytest.fixture(scope="module", autouse=True)
def setup_and_teardown():
    # beforeAll
    print("Setting up module")

    yield

    # afterAll
    print("Tearing down module")

"""

"""

---------------------------------------------

# NAMESPACE SEGRATATION

One folder(package)-scoped utils.py (for good utils function reusability)

- One test file per class.
  - One test class per concept (cohesion shall be judged based on invariants (invariant closely related to each other should be part of th same class))
    - One test function per low-level invariant to respect

# DOCSTRINGS

The test classes docstring MUST define an exhaustive-enough invariant list.
Test test functions docstring MUST define the low-elve invariant checked by the function AND why this invariant.

# TEST SUITE

What we need to test:

user role assignment
user_group role assignment
idp_group related role assignment ((with feature flag being set (should work) AND not being set (should fail)))

special case model: Permission, FilteringLabel, Actor

is_published (USE a dedicated test class for it (as it will make the future domain-scoped is_published PR easier))

test consistency (1 perm per/50 role/per 1 RoleAssignment IS THE SAME AS 50 perm/per 1 role/per 1 RoleAssignment)
test for special perms ("_full" suffix, special perm prefixes ("approve", "backup", "restore", etc...))
test is_active (inactive user shouldn't have any permission)
focus mode (check low level focus mode utils only)



The `_get_actor_accessible_ids` special case doesn't seem to be handled by (is_access_allowed AND is_object_accessible)
The `is_object_accessible` doesn't seem to take account for `Permission`
The `get_role_assignments_from_user` should block a `user` `User` if `user.is_active is False`

Folder.descendants creation/deletion

Function to test:

get_role_assignments_from_user
_get_role_assignments_from_permission (test for Permission + perm_prefix (including special ones))


Ensure the folder tree remains a DAG

PREVENT folder.objects.bulk_create(remove its usages from the codebase as it can cause problems)/folder.objects.bulk_update(via custom object manager i guess)
(to do later on)

CHECK HOW (builtin related perms) work (to also create dedicated tests for this invariant too).
===> Such test would have prevented the privilege escalation vuln so it's pretty important.


# NOTE:

The Folder.ContentType.ROOT is useless.
The Folder.builtin is also useless.

"""

_NAME_COUNTER: int = 0


def gen_name(name: str = "") -> str:
    """
    Generate a unique `name` for a DB object.

    This is usefull to avoid DB conflict + not think about pointless test object naming)
    """

    global _NAME_COUNTER
    _NAME_COUNTER += 1
    return f"P{_NAME_COUNTER}_{name}"


@dataclass
class Node:
    """Represent a `Folder` (a `Node` in the folder tree)."""

    name: str
    """Name for this folder (`Folder.name`)"""
    children: list[Node] = field(default_factory=list)
    """Represent the direct children `Folder`(domains) for this `Folder`(domain)."""


class Utils:
    @staticmethod
    def create_folder_tree(node: Node, *, parent_folder: Optional[Folder] = None):
        if parent_folder is None:
            parent_folder = Folder.get_root_folder()

        folder = Folder.objects.create(name=node.name, parent_folder=parent_folder)
        for child_node in node.children:
            Utils.create_folder_tree(child_node, parent_folder=folder)

    @staticmethod
    def check_folder_ancestors(folder: Folder, expected_ancestor_names: list[str]):
        """
        Check that if the `expected_ancestor_names` `Folder` name list matches the `folder.ancestors` ancestor folders.

        **WARNING:** The `expected_ancestor_names` SHALL NOT contain the root folder name.
        """

        ancestor_names = {
            ancestor.name
            for ancestor in folder.ancestors.all().exclude(
                content_type=Folder.ContentType.ROOT
            )
        }

        for expected_ancestor_name in expected_ancestor_names:
            if expected_ancestor_name not in ancestor_names:
                assert f"Expected ancestor {ancestor_names!r} not found in the folder ancestors."

            ancestor_names.remove(expected_ancestor_name)

        assert len(ancestor_names) == 0, (
            f"The following ancestor names: ({ancestor_names!r}) WHERE NOT FOUND in the expected_ancestor_names: {expected_ancestor_names!r}"
        )


@pytest.mark.django_db
class TestRootFolder:
    # TODO: Explain the invariants of the root folder.
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

        new_folder = Folder.objects.create(name=gen_name())

        try:
            root_folder.parent_folder = new_folder
            root_folder.save()
        except Folder.InconsistencyError:
            return
        except Exception:
            pass

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
        except Exception:
            pass

        assert root_folder.builtin is True, (
            "The root folder MUST be considered as builtin."
        )

    def test_root_folder_duplicate(self, root_folder: Folder):
        """Ensure there can't be multiple root folders."""

        try:
            Folder.objects.create(name="ABC", content_type=Folder.ContentType.ROOT)
        except Folder.InconsistencyError:
            return
        except Exception:
            pass

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
        except Exception:
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
                Folder.objects.create(name=gen_name(), parent_folder=None)
            except Folder.InconsistencyError:
                return
            except Exception:
                pass

            parentless_folder_count = Folder.objects.filter(parent_folder=None).count()
            assert parentless_folder_count == 1, (
                f"A newly created folder SHALL NOT be allowed to have no `parent_domain` (folder.content_type={content_type})."
            )

    def test_cycle_on_self(self):
        """Ensure there can't be a cycle (with a folder having itself as a `parent_folder`)."""

        folder = Folder.objects.create(name=gen_name())
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

        folder1 = Folder.objects.create(name=gen_name("folder1"))
        folder2 = Folder.objects.create(name=gen_name("folder2"), parent_folder=folder1)
        folder3 = Folder.objects.create(name=gen_name("folder3"), parent_folder=folder2)
        folder4 = Folder.objects.create(name=gen_name("folder4"), parent_folder=folder3)

        try:
            folder1.parent_folder = folder4
            folder1.save()
        except Folder.InconsistencyError:
            return
        except Exception:
            pass

        assert folder1.parent_folder != folder4, (
            "`folder4` is a descendant domain of `folder1`, therfore `folder1` MUST NOT have `folder4` as its parent (as it would create a cycle in the folder tree)."
        )


@pytest.mark.django_db
class TestFolderDescendants:
    """
    The `Folder.descendants` field is a `ManyToManyField` which MUST perfectly consistent to the current folder tree.

    This is very important as the IAM perform decisions based on this field.

    **INVARIANT:** The `Folder.descendants` field MUST always be consistent with the current state of the `iam_folder` SQL table.
    1. `Folder.descendants` MUST remain consistent on `folder.parent_folder` change.
    2. `Folder.descendants` MUST remain consistent on `Folder` creation.
    3. `Folder.descendants` MUST remain consistent on `Folder` deletion.
    """

    def test_parent_folder_change(self):
        """Ensure the `Folder.descendants` field is correctly updated when the `folder.parent_folder` changes."""

        Utils.create_folder_tree(
            Node(
                "folder_1",
                [
                    Node(
                        "folder_1_1",
                        [
                            Node(
                                "folder_1_1_1",
                                [
                                    Node("folder_1_1_1_1"),
                                    Node("folder_1_1_1_2"),
                                ],
                            )
                        ],
                    ),
                    Node(
                        "folder_1_2", [Node("folder_1_2_1", [Node("folder_2_1_1_1")])]
                    ),
                ],
            ),
        )

        folder = Folder.objects.get(name="folder_1_1_1_2")

        Utils.check_folder_ancestors(
            folder,
            [
                "folder_1",
                "folder_1_1",
                "folder_1_1_1",
            ],
        )

        folder.parent_folder = Folder.objects.get(name="folder_2_1_1_1")
        folder.save()

        Utils.check_folder_ancestors(
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

        Utils.create_folder_tree(
            Node(
                "folder_1",
                [
                    Node(
                        "folder_1_1",
                        [
                            Node(
                                "folder_1_1_1",
                                [
                                    Node("folder_1_1_1_1"),
                                ],
                            )
                        ],
                    ),
                    Node(
                        "folder_1_2", [Node("folder_1_2_1", [Node("folder_2_1_1_1")])]
                    ),
                ],
            ),
        )

        parent_folder = Folder.objects.get(name="folder_1_1_1_1")
        folder = Folder.objects.create(name="new_folder", parent_folder=parent_folder)

        Utils.check_folder_ancestors(
            folder,
            [
                "folder_1",
                "folder_1_1",
                "folder_1_1_1",
                "folder_1_1_1_1",
            ],
        )
