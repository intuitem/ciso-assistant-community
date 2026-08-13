from dataclasses import dataclass, field
from typing import Optional

from iam.models import Folder


@dataclass
class Node:
    """Represent a `Folder` (a `Node` in the folder tree)."""

    name: str
    """Name for this folder (`Folder.name`)"""
    children: list[Node] = field(default_factory=list)
    """Represent the direct children `Folder`(domains) for this `Folder`(domain)."""


def create_folder_tree(nodes: list[Node], *, parent_folder: Optional[Folder] = None):
    if parent_folder is None:
        parent_folder = Folder.get_root_folder()

    for node in nodes:
        folder = Folder.objects.create(name=node.name, parent_folder=parent_folder)
        for child_node in node.children:
            create_folder_tree([child_node], parent_folder=folder)


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
        is_ancestor_found = expected_ancestor_name in ancestor_names

        assert is_ancestor_found, (
            f"Expected ancestor {ancestor_names!r} not found in the folder ancestors."
        )

        ancestor_names.remove(expected_ancestor_name)

    assert len(ancestor_names) == 0, (
        f"The following ancestor names: ({ancestor_names!r}) WHERE NOT FOUND in the expected_ancestor_names: {expected_ancestor_names!r}"
    )
