"""Scales and rating outcomes of quick forms.

A scale is an ordered list of levels defined once on the form
(`scales_definition`), each optionally carrying a numeric `value`. A choice
question uses one with `config: {scale: <ref_id>}` instead of listing its
choices: on import it gets one choice per level, named
`<question urn>:choice:<level ref_id>`, so answers, scores and CEL only ever see
ordinary choices.

A rating outcome (`kind: rating` in `outcomes_definition`) measures each visible
page answering all its `dimensions` (scales) as a point, one per stage
(`config.stage` on its questions, "current" when absent), and classifies the point
into one of its named `levels`, either:

- `grid`, for exactly two dimensions: one row per level of the first, low to high,
  one cell per level of the second, low to high; or
- `rules`, for any number: `[{level, when}]`, the first CEL `when` that holds wins.
  It reads `dims.<scale>.level`, `.rank` (1-based) and `.value` (the level's
  `value`, its rank when it has none), both numbers written as decimals (`8.0`).

An optional `pages` list of page ids (as in `pages["…"]` in rules) limits which
pages a rating reads, so two ratings on the same scales stay apart. For the form's
rules, `values.<ref_id>` is the rank (1-based position in `levels`) of the highest
level among the current points, `values.<ref_id>_<stage>` the same for another
stage, and `ratings.<ref_id>.points` every point: page, stage, dims, level, rank.
"""

import celpy
import structlog
from django.utils.translation import get_language

logger = structlog.get_logger(__name__)

CURRENT = "current"


def scales_of(quick_form) -> dict:
    definition = (
        quick_form.get("scales_definition")
        if isinstance(quick_form, dict)
        else getattr(quick_form, "scales_definition", None)
    )
    return {
        scale["ref_id"]: scale
        for scale in definition or []
        if isinstance(scale, dict) and scale.get("ref_id")
    }


def ratings_of(outcomes_definition) -> list[dict]:
    return [
        rule
        for rule in outcomes_definition or []
        if isinstance(rule, dict)
        and rule.get("kind") == "rating"
        and rule.get("ref_id")
    ]


def page_id(urn) -> str:
    """A page's id in rules: `pages["<id>"]`."""
    from core.utils import extract_node_id

    return extract_node_id(str(urn or "")) or ""


def _config(question) -> dict:
    config = (
        question.get("config")
        if isinstance(question, dict)
        else getattr(question, "config", None)
    )
    return config if isinstance(config, dict) else {}


def expand_scales(quick_form: dict) -> dict:
    """Give every question that uses a scale and lists no choices one choice per
    level. In place, and returns the form."""
    scales = scales_of(quick_form)
    if not scales:
        return quick_form
    for page in quick_form.get("pages") or []:
        for urn, question in (page.get("questions") or {}).items():
            scale = scales.get(_config(question).get("scale"))
            if scale is None or question.get("choices"):
                continue
            question["choices"] = [
                _choice(urn, level) for level in scale.get("levels") or []
            ]
    return quick_form


def _choice(question_urn: str, level: dict) -> dict:
    choice = {
        "urn": f"{question_urn}:choice:{level['ref_id']}",
        "value": level.get("label") or level["ref_id"],
    }
    for key in ("description", "color"):
        if level.get(key):
            choice[key] = level[key]
    translations = {
        lang: {
            k: v
            for k, v in {
                "value": entry.get("label"),
                "description": entry.get("description"),
            }.items()
            if v
        }
        for lang, entry in (level.get("translations") or {}).items()
        if isinstance(entry, dict)
    }
    if translations:
        choice["translations"] = translations
    return choice


def _dim(scale: dict, level_ref: str) -> dict:
    refs = [lvl["ref_id"] for lvl in scale.get("levels") or []]
    rank = refs.index(level_ref) + 1
    value = scale["levels"][rank - 1].get("value")
    # Numbers in CEL are doubles, as `values.*` are: an int rank would refuse to
    # multiply a value.
    return {
        "level": level_ref,
        "rank": float(rank),
        "value": float(value) if isinstance(value, (int, float)) else float(rank),
    }


def _compile_rules(rating: dict) -> list:
    env = celpy.Environment()
    programs = []
    for rule in rating.get("rules") or []:
        try:
            programs.append((rule["level"], env.program(env.compile(rule["when"]))))
        except Exception as e:
            logger.warning("rating_rule_invalid", rating=rating.get("ref_id"), error=e)
    return programs


def _classify(rating: dict, dims: dict, programs: list) -> str | None:
    """The rating's level for a point's dimensions, or None."""
    names = rating.get("dimensions") or []
    if rating.get("grid") is not None:
        try:
            row = int(dims[names[0]]["rank"]) - 1
            cell = int(dims[names[1]]["rank"]) - 1
            return rating["grid"][row][cell]
        except IndexError, KeyError, TypeError:
            return None
    from core.cel_service import _python_to_cel

    context = {"dims": _python_to_cel(dims)}
    for level, program in programs:
        try:
            if program.evaluate(context):
                return level
        except Exception as e:
            logger.warning("rating_rule_error", rating=rating.get("ref_id"), error=e)
    return None


def scales_error(quick_form: dict) -> str | None:
    """Why the form's scales or rating outcomes cannot work, or None. Checked
    before `expand_scales`, so library input of any shape gets an answer."""
    definition = quick_form.get("scales_definition")
    if definition is not None and (
        not isinstance(definition, list)
        or not all(
            isinstance(s, dict) and isinstance(s.get("ref_id"), str) for s in definition
        )
    ):
        return "scales_definition must be a list of scales, each with a ref_id"
    scales = scales_of(quick_form)
    for scale in scales.values():
        levels = scale.get("levels")
        if not isinstance(levels, list) or not all(
            isinstance(lvl, dict) for lvl in levels
        ):
            return f"scale {scale['ref_id']}: levels must be a list of objects"
        refs = [lvl.get("ref_id") for lvl in levels]
        if (
            not refs
            or not all(isinstance(r, str) and r for r in refs)
            or len(set(refs)) != len(refs)
        ):
            return f"scale {scale['ref_id']}: every level needs a unique ref_id"
    pages = quick_form.get("pages") or []
    if not isinstance(pages, list) or not all(isinstance(p, dict) for p in pages):
        return "pages must be a list of objects"
    for page in pages:
        questions = page.get("questions") or {}
        if not isinstance(questions, dict):
            continue  # the page importer reports it
        for urn, question in questions.items():
            scale = _config(question).get("scale")
            if scale is not None and (
                not isinstance(scale, str) or scale not in scales
            ):
                return f"question {urn} uses unknown scale {scale}"
    page_ids = {page_id(page.get("urn")) for page in pages}
    for rating in ratings_of(quick_form.get("outcomes_definition")):
        ref = rating["ref_id"]
        names = rating.get("dimensions") or []
        if (
            not isinstance(names, list)
            or not names
            or any(not isinstance(n, str) or n not in scales for n in names)
        ):
            return f"rating {ref}: dimensions must name scales of the form"
        levels = [
            lvl.get("ref_id")
            for lvl in rating.get("levels") or []
            if isinstance(lvl, dict)
        ]
        if not levels or not all(levels):
            return f"rating {ref}: every level needs a ref_id"
        grid, rules = rating.get("grid"), rating.get("rules")
        if (grid is None) == (rules is None):
            return f"rating {ref}: classify with either a grid or rules"
        if grid is not None:
            if len(names) != 2:
                return f"rating {ref}: a grid needs exactly two dimensions"
            rows, cells = (len(scales[n].get("levels") or []) for n in names)
            if (
                not isinstance(grid, list)
                or len(grid) != rows
                or any(not isinstance(row, list) or len(row) != cells for row in grid)
            ):
                return (
                    f"rating {ref}: the grid needs one row per {names[0]} level "
                    f"and one cell per {names[1]} level"
                )
            if any(cell not in levels for row in grid for cell in row):
                return f"rating {ref}: every grid cell must be one of its levels"
        else:
            if not isinstance(rules, list) or not rules:
                return f"rating {ref}: rules need at least one entry"
            env = celpy.Environment()
            for rule in rules:
                if not isinstance(rule, dict) or rule.get("level") not in levels:
                    return f"rating {ref}: every rule must name one of its levels"
                try:
                    env.compile(str(rule.get("when") or ""))
                except Exception:
                    return f"rating {ref}: rule for {rule['level']} is not valid CEL"
        scoped = rating.get("pages") or []
        if not isinstance(scoped, list) or not all(isinstance(p, str) for p in scoped):
            return f"rating {ref}: pages must be a list of page ids"
        if unknown := set(scoped) - page_ids:
            return f"rating {ref}: unknown page {sorted(unknown)[0]}"
    return None


def evaluate_ratings(quick_form, pages: list[dict]) -> tuple[dict, list[dict]]:
    """Points and CEL values of the form's rating outcomes.

    `pages`: the visible pages in order, each {"urn", "answers": [(question config,
    selected choice urn or None)]}. Returns ({value name: float}, [{"ref_id",
    "points": [{"page", "stage", "dims", "level", "rank"}]}]), levels named by
    ref_id, `page` by URN. A point with no matching rule has no level.
    """
    outcomes = (
        quick_form.get("outcomes_definition")
        if isinstance(quick_form, dict)
        else quick_form.outcomes_definition
    )
    ratings = ratings_of(outcomes)
    if not ratings:
        return {}, []
    scales = scales_of(quick_form)
    values: dict[str, float] = {}
    results = []
    for rating in ratings:
        names = rating.get("dimensions") or []
        if not names or any(name not in scales for name in names):
            continue
        level_refs = [lvl.get("ref_id") for lvl in rating.get("levels") or []]
        programs = _compile_rules(rating) if rating.get("grid") is None else []
        scope = set(rating.get("pages") or [])
        points = []
        for page in pages:
            if scope and page_id(page["urn"]) not in scope:
                continue
            by_stage: dict[str, dict] = {}
            for config, choice_urn in page["answers"]:
                scale = config.get("scale")
                if scale not in names or not choice_urn:
                    continue
                level_ref = str(choice_urn).rsplit(":", 1)[-1]
                if level_ref not in [l["ref_id"] for l in scales[scale]["levels"]]:
                    continue
                by_stage.setdefault(config.get("stage") or CURRENT, {})[scale] = _dim(
                    scales[scale], level_ref
                )
            for stage, dims in by_stage.items():
                if set(dims) != set(names):
                    continue
                level = _classify(rating, dims, programs)
                points.append(
                    {
                        "page": page["urn"],
                        "stage": stage,
                        "dims": dims,
                        "level": level,
                        "rank": level_refs.index(level) + 1
                        if level in level_refs
                        else 0,
                    }
                )
        for stage in {p["stage"] for p in points}:
            ranks = [p["rank"] for p in points if p["stage"] == stage and p["rank"]]
            if ranks:
                name = (
                    rating["ref_id"]
                    if stage == CURRENT
                    else f"{rating['ref_id']}_{stage}"
                )
                values[name] = float(max(ranks))
        results.append({"ref_id": rating["ref_id"], "points": points})
    return values, results


def _translated(entry: dict, field: str, lang: str) -> str:
    translation = (entry.get("translations") or {}).get(lang) or {}
    return translation.get(field) or entry.get(field) or entry.get("ref_id") or ""


def ratings_for_display(quick_form, results: list[dict]) -> list[dict]:
    """The rating outcomes with their dimensions and points, labels in the active
    language, for the response page. Two-dimensional ratings get their `grid`,
    worked out from the rules when they have no grid of their own."""
    lang = (get_language() or "en").split("-")[0]
    scales = scales_of(quick_form)
    points_by_ref = {r["ref_id"]: r["points"] for r in results}
    display = []
    outcomes = (
        quick_form.get("outcomes_definition")
        if isinstance(quick_form, dict)
        else quick_form.outcomes_definition
    )
    for rating in ratings_of(outcomes):
        names = rating.get("dimensions") or []
        if not names or any(name not in scales for name in names):
            continue
        grid = rating.get("grid")
        if grid is None and len(names) == 2:
            programs = _compile_rules(rating)
            grid = [
                [
                    _classify(
                        rating,
                        {
                            names[0]: _dim(scales[names[0]], row["ref_id"]),
                            names[1]: _dim(scales[names[1]], cell["ref_id"]),
                        },
                        programs,
                    )
                    for cell in scales[names[1]]["levels"]
                ]
                for row in scales[names[0]]["levels"]
            ]
        display.append(
            {
                "ref_id": rating["ref_id"],
                "label": _translated(rating, "label", lang),
                "dimensions": [
                    {
                        "ref_id": name,
                        "label": _translated(scales[name], "label", lang),
                        "levels": [
                            {
                                "ref_id": lvl["ref_id"],
                                "label": _translated(lvl, "label", lang),
                                "description": _translated(lvl, "description", lang)
                                if lvl.get("description")
                                else "",
                            }
                            for lvl in scales[name].get("levels") or []
                        ],
                    }
                    for name in names
                ],
                "levels": [
                    {
                        "ref_id": lvl["ref_id"],
                        "label": _translated(lvl, "label", lang),
                        "color": lvl.get("color") or "",
                    }
                    for lvl in rating.get("levels") or []
                ],
                "grid": grid,
                "points": points_by_ref.get(rating["ref_id"], []),
            }
        )
    return display


def value_names(quick_form: dict) -> list[str]:
    """The CEL values the form's rating outcomes can produce."""
    stages = {
        _config(question).get("stage")
        for page in quick_form.get("pages") or []
        for question in (page.get("questions") or {}).values()
        if _config(question).get("scale")
    } - {None, "", CURRENT}
    return [
        name
        for rating in ratings_of(quick_form.get("outcomes_definition"))
        for name in [
            rating["ref_id"],
            *(f"{rating['ref_id']}_{s}" for s in sorted(stages)),
        ]
    ]


def cel_ratings(results: list[dict]) -> dict:
    """The `ratings` CEL root: every point of each rating outcome."""
    return {r["ref_id"]: {"points": r["points"]} for r in results}


def probe_ratings(quick_form: dict) -> dict:
    """`ratings` as rules see it, with one point of the real shape, for checks."""
    dim = {"level": "", "rank": 1.0, "value": 1.0}
    return {
        rating["ref_id"]: {
            "points": [
                {
                    "page": "",
                    "stage": CURRENT,
                    "dims": {name: dim for name in rating.get("dimensions") or []},
                    "level": "",
                    "rank": 1,
                }
            ]
        }
        for rating in ratings_of(quick_form.get("outcomes_definition"))
    }
