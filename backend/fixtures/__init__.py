from importlib.abc import Traversable
import importlib.resources

_PACKAGE_RESOURCES = importlib.resources.files("fixtures")


def get_resource_path(resource_name: str) -> Traversable:
    """
    Get the absolute path to a resource in the fixtures package.

    Args:
        resource_name (str): The name of the resource file.

    Returns:
        str: The absolute path to the resource file.
    """
    return _PACKAGE_RESOURCES / resource_name
