from django import template

register = template.Library()


@register.filter
def selected_option_index(optgroups: list) -> int:
    """
    Returns the index of the selected option in the given optgroups.

    Args:
        optgroups: the optgroups to check

    Returns:
        The index of the selected option in the given optgroups
    """
    for option_tuple in optgroups:
        for option in enumerate(option_tuple[1]):
            if option[1]["selected"]:
                return option[1]["index"]
    return 0


@register.filter
def selected_option_label(optgroups: list) -> str:
    """
    Returns the label of the selected option in the given optgroups.

    Args:
        optgroups: the optgroups to check

    Returns:
        The label of the selected option in the given optgroups
    """
    for option_tuple in optgroups:
        for option in enumerate(option_tuple[1]):
            if option[1]["selected"]:
                return option[1]["label"]
    return ""
