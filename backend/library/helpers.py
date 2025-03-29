import json

# from core.models import RequirementNode
from django.utils.translation import get_language

from typing import Union


def get_referential_translation(object, parameter: str, locale=None) -> str | list:
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
    _object = object
    fallback = (
        _object.get(parameter)
        if isinstance(_object, dict)
        else _object.__dict__.get(parameter)
    )
    if isinstance(fallback, list):
        translations = [t.get("translations", {}) for t in fallback]
        locale_translations = fallback
        for i in range(len(locale_translations)):
            for key in translations[i].get(locale, {}).keys():
                locale_translations[i][key] = translations[i].get(locale, {}).get(key)
        return locale_translations or fallback
    translations = (
        _object.get("translations", {})
        if isinstance(_object, dict)
        else _object.translations
    )
    if not translations:
        return fallback
    locale_translations = (
        translations.get(locale, {}) if locale else translations.get(get_language(), {})
    )
    return locale_translations.get(parameter, fallback)


def update_translations_in_object(obj: Union[dict, list], locale=None):
    """
    Recursively update the translations of 'name' and 'description' fields in a dict or a list.

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

    elif isinstance(obj, list):
        for i in range(len(obj)):
            obj[i] = update_translations_in_object(obj[i])

    return obj


def update_translations(data_dict: Union[dict, list], locale=None) -> Union[dict, list]:
    """
    Update the translations of 'name' and 'description' fields in a dictionary or list of objects.

    Args:
        data_dict (Union[dict, list]): The JSON string dict or list of objects to update.
        locale (str): The locale to get the translation for.

    Returns:
        Union[dict, list]: The translated objects.
    """
    if isinstance(data_dict, dict):
        for key, objects_list in data_dict.items():
            if isinstance(objects_list, list):
                for obj in objects_list:
                    update_translations_in_object(obj, get_language() or locale)
        return data_dict
    elif isinstance(data_dict, list):
        for obj in data_dict:
            update_translations_in_object(obj, get_language() or locale)
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
