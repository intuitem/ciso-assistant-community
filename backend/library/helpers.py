import json
from core.models import RequirementNode
from django.utils.translation import get_language


def get_referential_translation(object, parameter: str, locale=None) -> str:
    # NOTE: put get_language() as default value for locale doesn't work, default locale "en" is always returned.
    # get_language() needs to be called in the actual thread to get the current language, it could explain that behavior.
    """
    Get the translation of a referential object in a specific locale, if it exists.

    Args:
        object (dict): The referential object to get the translation for
        locale (str): The locale to get the translation for
        parameter (str): The parameter to get the translation for

    Returns:
        str: The translation in the specified locale, or the default value if it does not exist
    """
    print(get_language())
    translations = object.get("translations", {})
    locale_translations = translations.get(locale, {}) if locale else translations.get(get_language(), {})
    return locale_translations.get(parameter, object.get(parameter))

def update_translations_in_object(obj, locale: str):
    """
    Recursively update the translations of 'name' and 'description' fields in an object.

    Args:
        obj (dict): The object to update.
        locale (str): The locale to get the translation for.
    """
    if isinstance(obj, dict):
        if "translations" in obj:
            obj["name"] = get_referential_translation(obj, "name")
            obj["description"] = get_referential_translation(obj, "description")
            obj["abbreviation"] = get_referential_translation(obj, "abbreviation")
        
        for key, value in obj.items():
            if isinstance(value, dict):
                update_translations_in_object(value, locale)
            elif isinstance(value, list):
                for item in value:
                    update_translations_in_object(item, locale)

def update_translations(data_dict_str, locale=None) -> str:
    """
    Update the translations of 'name' and 'description' fields in a dictionary of objects.

    Args:
        data_dict_str (str): The JSON string of the dict of objects to update.
        locale (str): The locale to get the translation for.

    Returns:
        str: The updated dictionary as a JSON string.
    """
    data_dict = json.loads(data_dict_str)
    for key, objects_list in data_dict.items():
        if isinstance(objects_list, list):
            for obj in objects_list:
                update_translations_in_object(obj, locale)
                
    return json.dumps(data_dict)

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
