"""
Risk-level vocabulary resolved from the risk matrix.

A scenario's current/residual/inherent level is an index into the matrix's
``risk`` array; the labels live in the matrix library object and differ per
matrix and per locale, so everything here reads them back from the definition.
"""

import re

from django.utils.translation import get_language

NOT_RATED = "--"

# Matrix labels are often decorated with their rank ("4 - high", "[3] moyen").
_DECORATION = re.compile(r"^[\W\d_]+|[\W\d_]+$", re.UNICODE)

# Scope name → RiskScenario field holding that scope's level
LEVEL_FIELDS = {
    "current": "current_level",
    "residual": "residual_level",
    "inherent": "inherent_level",
}


def _risk_defs(matrix) -> list[dict]:
    definition = getattr(matrix, "json_definition", None) or {}
    return definition.get("risk") or []


def _translated(entry: dict, key: str, locale: str | None) -> str:
    if locale:
        value = (entry.get("translations") or {}).get(locale, {}).get(key)
        if value:
            return value
    return entry.get(key) or ""


def level_label(matrix, level: int | None, locale: str | None = None) -> str:
    """Human label for a risk level index, per the matrix's own wording."""
    if level is None or level < 0:
        return NOT_RATED
    defs = _risk_defs(matrix)
    if not defs:
        return NOT_RATED
    if level >= len(defs):
        return str(level)
    locale = locale or get_language()
    return _translated(defs[level], "name", locale) or str(level)


def _normalize(text: str) -> str:
    return _DECORATION.sub("", " ".join(str(text).split())).casefold()


def _level_aliases(matrix) -> dict[str, set[int]]:
    """Every term the matrix knows for each level → level index."""
    aliases: dict[str, set[int]] = {}

    def register(text, index: int) -> None:
        if not isinstance(text, str) or not text.strip():
            return
        aliases.setdefault(text.strip().casefold(), set()).add(index)
        normalized = _normalize(text)
        if normalized:
            aliases.setdefault(normalized, set()).add(index)

    for index, entry in enumerate(_risk_defs(matrix)):
        register(entry.get("name"), index)
        register(entry.get("abbreviation"), index)
        for translation in (entry.get("translations") or {}).values():
            if isinstance(translation, dict):
                register(translation.get("name"), index)
                register(translation.get("abbreviation"), index)
        aliases.setdefault(str(index), set()).add(index)

    return aliases


def resolve_levels_by_matrix(term: str, matrices) -> dict[str, set[int]]:
    """
    Resolve a level term per matrix — level 2 in a 3-level matrix is not level 2
    in a 5-level one, so a shared index set would miscount.
    """
    if not term:
        return {}
    # Exact first: stripping decoration collapses labels that differ only by
    # rank ("Level 4" and "Level 5" both normalize to "level"), so the
    # normalized form is a fallback, never an addition.
    exact = str(term).strip().casefold()
    normalized = _normalize(term)

    resolved: dict[str, set[int]] = {}
    for matrix in matrices:
        aliases = _level_aliases(matrix)
        levels = set(aliases.get(exact, set()))
        if not levels and normalized:
            levels = set(aliases.get(normalized, set()))
        if levels:
            resolved[str(matrix.id)] = levels
    return resolved


def known_level_names(matrices, locale: str | None = None) -> list[str]:
    """Level names available across the matrices, lowest to highest, deduplicated."""
    locale = locale or get_language()
    names: list[str] = []
    for matrix in matrices:
        for entry in _risk_defs(matrix):
            name = _translated(entry, "name", locale)
            if name and name not in names:
                names.append(name)
    return names


def describe_levels(matrix, locale: str | None = None) -> str:
    """One-line ordered vocabulary of a matrix's risk levels, lowest to highest."""
    defs = _risk_defs(matrix)
    if not defs:
        return ""
    locale = locale or get_language()
    return " < ".join(
        _translated(entry, "name", locale) or str(index)
        for index, entry in enumerate(defs)
    )


def matrices_for_scenarios(queryset):
    """Distinct risk matrices behind a RiskScenario queryset."""
    from django.apps import apps

    matrix_ids = {
        mid
        for mid in queryset.values_list(
            "risk_assessment__risk_matrix_id", flat=True
        ).distinct()
        if mid
    }
    if not matrix_ids:
        return []
    RiskMatrix = apps.get_model("core", "RiskMatrix")
    return list(RiskMatrix.objects.filter(id__in=matrix_ids))
