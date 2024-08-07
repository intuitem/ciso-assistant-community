import json

# from core.models import RequirementNode
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
    fallback = (
        object.get(parameter)
        if isinstance(object, dict)
        else object.__dict__.get(parameter)
    )
    translations = (
        object.get("translations", {})
        if isinstance(object, dict)
        else object.translations
    )
    if not translations:
        return fallback
    locale_translations = (
        translations.get(locale, {}) if locale else translations.get(get_language(), {})
    )
    return locale_translations.get(parameter, fallback)


def update_translations_in_object(obj, locale=None):
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
            obj["annotation"] = get_referential_translation(obj, "annotation")

        for key, value in obj.items():
            if isinstance(value, dict):
                update_translations_in_object(value, get_language() or locale)
            elif isinstance(value, list):
                for item in value:
                    update_translations_in_object(item, get_language() or locale)
    return obj


def update_translations(data_dict_str, locale=None) -> str:
    """
    Update the translations of 'name' and 'description' fields in a dictionary of objects.

    Args:
        data_dict_str (str): The JSON string of the dict of objects to update.
        locale (str): The locale to get the translation for.

    Returns:
        str: The updated dictionary.
    """
    if isinstance(data_dict_str, str):
        data_dict = json.loads(data_dict_str)
        for key, objects_list in data_dict.items():
            if isinstance(objects_list, list):
                for obj in objects_list:
                    update_translations_in_object(obj, get_language() or locale)
    elif isinstance(data_dict_str, list):
        for obj in data_dict_str:
            update_translations_in_object(obj, get_language() or locale)
        return data_dict_str
    return data_dict


def update_translations_as_string(data_dict_str, locale=None) -> str:
    """
    Update the translations of 'name' and 'description' fields in a dictionary of objects.

    Args:
        data_dict_str (str): The JSON string of the dict of objects to update.
        locale (str): The locale to get the translation for.

    Returns:
        str: The updated dictionary as a JSON string.
    """
    return json.dumps(update_translations(data_dict_str, locale))
