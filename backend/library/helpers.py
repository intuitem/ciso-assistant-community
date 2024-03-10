from core.models import RequirementNode
from iam.models import Folder


def preview_library(library) -> dict[str, list]:
    """
    Function to create temporary requirement nodes list
    Used to display requirements in tree view inside library detail view
    """
    preview = {}
    requirement_nodes_list = []
    if library["objects"]["framework"].get("requirement_nodes"):
        index = 0
        for requirement_node in library["objects"]["framework"]["requirement_nodes"]:
            index += 1
            requirement_nodes_list.append(
                RequirementNode(
                    description=requirement_node.get("description"),
                    ref_id=requirement_node.get("ref_id"),
                    name=requirement_node.get("name"),
                    urn=requirement_node["urn"],
                    parent_urn=requirement_node.get("parent_urn"),
                    order_id=index,
                )
            )
    preview["requirement_nodes"] = requirement_nodes_list
    return preview
