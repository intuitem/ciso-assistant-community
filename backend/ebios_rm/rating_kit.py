"""
EBIOS RM rating scales carried by the study's risk matrix.

A matrix may define an optional `ebios_rm` section in its JSON definition:

    ebios_rm:
      ro_to:                                             # workshop 2
        motivation | resources | activity | pertinence: [{name, description}] x 4
        pertinence_grid: [[...]]                         # motivation x resources -> pertinence (0-based)
      success_probability: [{name, description}, ...]   # workshop 4, one per probability level
      technical_difficulty: [{name, description}, ...]  # workshop 4, one per probability level
      likelihood_grid: [[...]]                           # probability x difficulty -> probability level

Anything missing falls back to the defaults below (fiche méthode 8 resampled to
the matrix size, and the historical RO/TO scales), so a matrix without the
section behaves as before. Default levels carry `"default": True`: their names
are i18n keys the frontend translates, whereas custom names are shown as written.
"""

from ebios_rm.quotation import default_likelihood_grid

RO_TO_SCALE_SIZE = 4

DEFAULT_SUCCESS_PROBABILITY = [
    "successProbabilityVeryLow",
    "successProbabilityLow",
    "successProbabilitySignificant",
    "successProbabilityVeryHigh",
    "successProbabilityNearCertain",
]
DEFAULT_TECHNICAL_DIFFICULTY = [
    "difficultyNegligible",
    "difficultyLow",
    "difficultyModerate",
    "difficultyHigh",
    "difficultyVeryHigh",
]
DEFAULT_RO_TO = {
    "motivation": ["very_low", "low", "significant", "strong"],
    "resources": ["limited", "significant", "important", "unlimited"],
    "activity": ["very_low", "low", "moderate", "important"],
    "pertinence": [
        "irrelevant",
        "partially_relevant",
        "fairly_relevant",
        "highly_relevant",
    ],
}
DEFAULT_PERTINENCE_GRID = [
    [0, 0, 1, 1],
    [0, 1, 2, 2],
    [1, 2, 2, 3],
    [1, 2, 3, 3],
]
RO_TO_SCALES = tuple(DEFAULT_RO_TO)


def _level(name: str) -> dict:
    return {"name": name, "default": True}


def _resample(names: list[str], size: int) -> list[dict]:
    if size < 2:
        return [_level(names[0]) for _ in range(size)]
    last = len(names) - 1
    return [_level(names[round(level * last / (size - 1))]) for level in range(size)]


def default_section(size: int) -> dict:
    return {
        "ro_to": {
            **{
                scale: [_level(name) for name in names]
                for scale, names in DEFAULT_RO_TO.items()
            },
            "pertinence_grid": [list(row) for row in DEFAULT_PERTINENCE_GRID],
        },
        "success_probability": (
            [_level(name) for name in DEFAULT_SUCCESS_PROBABILITY[1:]]
            if size == 4
            else _resample(DEFAULT_SUCCESS_PROBABILITY, size)
        ),
        "technical_difficulty": _resample(DEFAULT_TECHNICAL_DIFFICULTY, size),
        "likelihood_grid": default_likelihood_grid(size),
    }


def resolve(json_definition: dict) -> dict:
    """The matrix's EBIOS RM section with defaults filled in."""
    size = len(json_definition.get("probability") or [])
    defaults = default_section(size)
    section = json_definition.get("ebios_rm") or {}
    ro_to = section.get("ro_to") or {}
    return {
        "ro_to": {
            key: ro_to.get(key) or default for key, default in defaults["ro_to"].items()
        },
        "success_probability": section.get("success_probability")
        or defaults["success_probability"],
        "technical_difficulty": section.get("technical_difficulty")
        or defaults["technical_difficulty"],
        "likelihood_grid": section.get("likelihood_grid")
        or defaults["likelihood_grid"],
    }


def _check_levels(errors, label, levels, size):
    if not isinstance(levels, list) or len(levels) != size:
        errors.append(f"'{label}' must list {size} levels.")
        return
    for index, level in enumerate(levels):
        if not isinstance(level, dict) or not level.get("name"):
            errors.append(f"{label}[{index}] is missing a name.")


def _check_grid(errors, label, grid, rows, columns, values):
    if not isinstance(grid, list) or len(grid) != rows:
        errors.append(f"'{label}' must have {rows} rows.")
        return
    for i, row in enumerate(grid):
        if not isinstance(row, list) or len(row) != columns:
            errors.append(f"'{label}' row {i} must have {columns} cells.")
            continue
        for j, value in enumerate(row):
            if isinstance(value, bool) or not isinstance(value, int):
                errors.append(f"'{label}' cell [{i}][{j}] must be an integer.")
            elif not 0 <= value < values:
                errors.append(
                    f"'{label}' cell [{i}][{j}] must be between 0 and {values - 1}."
                )


def validate(section, probability_size: int) -> list[str]:
    """Errors in a matrix's `ebios_rm` section; every key is optional."""
    if section is None:
        return []
    if not isinstance(section, dict):
        return ["'ebios_rm' must be an object."]
    errors: list[str] = []
    prefix = "ebios_rm."
    for key in ("success_probability", "technical_difficulty"):
        if key in section:
            _check_levels(errors, prefix + key, section[key], probability_size)
    if "likelihood_grid" in section:
        _check_grid(
            errors,
            prefix + "likelihood_grid",
            section["likelihood_grid"],
            probability_size,
            probability_size,
            probability_size,
        )
    ro_to = section.get("ro_to")
    if ro_to is not None:
        if not isinstance(ro_to, dict):
            errors.append("'ebios_rm.ro_to' must be an object.")
        else:
            for key in RO_TO_SCALES:
                if key in ro_to:
                    _check_levels(
                        errors, f"{prefix}ro_to.{key}", ro_to[key], RO_TO_SCALE_SIZE
                    )
            if "pertinence_grid" in ro_to:
                _check_grid(
                    errors,
                    prefix + "ro_to.pertinence_grid",
                    ro_to["pertinence_grid"],
                    RO_TO_SCALE_SIZE,
                    RO_TO_SCALE_SIZE,
                    RO_TO_SCALE_SIZE,
                )
    return errors


def pertinence(ro_to_section: dict, motivation: int, resources: int) -> int:
    """Stored pertinence: 0 when undefined, else 1-based level from the grid."""
    if not motivation or not resources:
        return 0
    return ro_to_section["pertinence_grid"][motivation - 1][resources - 1] + 1
