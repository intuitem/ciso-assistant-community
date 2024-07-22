from core.models import RequirementNode
from django.utils.translation import get_language


def get_referential_translation(object, parameter: str, locale=None) -> str:
    # NOTE: put get_language() as default value for locale doesn't work, default locale "en" is always returned.
    # get_language() needs to be called in the actual thread to get the current language, it could explain that behavior.
    """
    Get the translation of a referential object in a specific locale, if it exists.

    Args:
        object (ReferentialObject)
        locale (str): The locale to get the translation for
        parameter (str): The parameter to get the translation for

    Returns:
        str: The translation in the specified locale, or the default value if it does not exist
    """
    translations = object.get("translations", {})
    locale_translations = translations.get(locale, {}) if locale else translations.get(get_language(), {})
    return locale_translations.get(parameter, object.get(parameter))

# Change the name of this function
def preview_library(framework: dict) -> dict[str, list]:
    """
    Function to create temporary requirement nodes list
    Used to display requirements in tree view inside library detail view
    """
    preview = {}
    requirement_nodes_list = []
    if framework.get("requirement_nodes"):
        index = 0
        for requirement_node in framework["requirement_nodes"]:
            index += 1
            requirement_nodes_list.append(
                RequirementNode(
                    description=get_referential_translation(requirement_node, "description"),
                    ref_id=requirement_node.get("ref_id"),
                    name=get_referential_translation(requirement_node, "name"),
                    urn=requirement_node["urn"],
                    parent_urn=requirement_node.get("parent_urn"),
                    order_id=index,
                )
            )
    preview["requirement_nodes"] = requirement_nodes_list
    return preview
