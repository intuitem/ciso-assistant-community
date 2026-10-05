"""
Bridge between the library-draft document and the visual editor for quick
forms.

A quick form is stored in the draft as the library-YAML object
({urn, ref_id, name, ..., outcomes_definition, scores_definition, pages}):
pages are a flat ordered list, each page holding `questions` keyed by URN
exactly like a requirement node. The visual editor is the FrameworkBuilder in
its quick-form mode, which speaks the framework editor doc
({framework_meta, nodes, questions, choices}) with pages as one-level nodes.

This module reuses framework_editor for the heavy lifting (URN stability and
minting, question/choice canonicalization) by presenting the quick form as a
pseudo-framework whose requirement_nodes are its pages, then strips the
framework-only vocabulary on the way back.
"""

import re

from core.utils import extract_node_id
from library.builder import BuilderError
from library.framework_editor import (
    editor_doc_to_framework_object,
    framework_to_editor_doc,
)

# Where a rule names a page, a question or a choice by node id. Only these
# positions are rewritten: a bare string elsewhere (`value == "2"`) is data.
_SUBSCRIPT = re.compile(r"""\b(pages|answers)\[\s*(["'])(.*?)\2\s*\]""")
_CHOICE_IN = re.compile(r"""(["'])([^"'\\]*)\1(\s+in\s+answers\s*\[)""")


def node_id_maps(urn_map: dict) -> tuple[dict, dict, dict]:
    """(pages, questions, choices) node-id renames implied by a save's URN map:
    a rule written before the first save names the editor's ids."""
    pages, questions, choices = {}, {}, {}
    for old, new in urn_map.items():
        if ":" not in old:  # editor-local ids, not URNs
            continue
        old_id, new_id = extract_node_id(old), extract_node_id(new)
        if not old_id or not new_id or old_id == new_id:
            continue
        if ":choice:" in new:
            choices[old_id] = new_id
        elif ":question:" in new:
            questions[old_id] = new_id
        else:
            pages[old_id] = new_id
    return pages, questions, choices


def rebase_expression(expression, maps):
    """The expression with renamed page/question/choice ids, in reference
    positions only. Mirrored by `rebaseExpression` in the builder."""
    if not expression:
        return expression
    pages, questions, choices = maps

    def subscript(match):
        new = (pages if match[1] == "pages" else questions).get(match[3])
        return match[0] if new is None else f"{match[1]}[{match[2]}{new}{match[2]}]"

    def choice(match):
        new = choices.get(match[2])
        return match[0] if new is None else f"{match[1]}{new}{match[1]}{match[3]}"

    return _CHOICE_IN.sub(choice, _SUBSCRIPT.sub(subscript, expression))


# Node-level keys that only make sense on requirement nodes.
FRAMEWORK_ONLY_NODE_KEYS = {
    "assessable",
    "depth",
    "parent_urn",
    "implementation_groups",
    "typical_evidence",
    "importance",
    "display_mode",
    "threats",
    "reference_controls",
    "weight",
}

# Framework-level keys that only make sense on frameworks.
FRAMEWORK_ONLY_META_KEYS = {
    "min_score",
    "max_score",
    "implementation_groups_definition",
    "field_visibility",
}


def page_base_urn(quick_form_urn: str) -> str:
    quick_form_urn = quick_form_urn.lower()
    if ":quick_form:" in quick_form_urn:
        return quick_form_urn.replace(":quick_form:", ":qf_page:", 1)
    return f"{quick_form_urn}:qf_page"


def quick_form_to_editor_doc(quick_form: dict, *, locale: str = "en") -> dict:
    """Convert a library-YAML quick form object into the editor doc shape."""
    pseudo = {key: value for key, value in quick_form.items() if key != "pages"}
    pseudo["requirement_nodes"] = [
        {**page, "assessable": True, "depth": 1}
        for page in quick_form.get("pages") or []
        if isinstance(page, dict)
    ]
    doc = framework_to_editor_doc(pseudo, locale=locale)
    doc["kind"] = "quick_form"
    doc["framework_meta"]["kind"] = "quick_form"
    doc["framework_meta"]["subject_question_urn"] = (
        quick_form.get("subject_question_urn") or None
    )
    doc["framework_meta"]["on_accept"] = quick_form.get("on_accept") or []
    for key in FRAMEWORK_ONLY_META_KEYS:
        doc["framework_meta"].pop(key, None)
    return doc


def editor_doc_to_quick_form_object(
    editor_doc: dict, *, existing: dict, urn_map_out: dict | None = None
) -> dict:
    """Convert an editor doc back into the library-YAML quick form object.

    `existing` is the quick form object currently in the draft document; it
    pins the form URN and the set of known page/question/choice URNs.
    """
    form_urn = str(existing.get("urn", "")).lower()
    if not form_urn:
        raise BuilderError("The quick form in the draft has no URN")
    pseudo_existing = {key: value for key, value in existing.items() if key != "pages"}
    pseudo_existing["requirement_nodes"] = list(existing.get("pages") or [])
    for node in editor_doc.get("nodes") or []:
        if node.get("parent_urn"):
            raise BuilderError("Quick form pages cannot be nested")
    urn_map: dict = {}
    result = editor_doc_to_framework_object(
        editor_doc,
        existing=pseudo_existing,
        node_base=page_base_urn(form_urn),
        urn_map_out=urn_map,
    )
    if urn_map_out is not None:
        urn_map_out.update(urn_map)
    pages = []
    for node in result.pop("requirement_nodes", []):
        pages.append(
            {
                key: value
                for key, value in node.items()
                if key not in FRAMEWORK_ONLY_NODE_KEYS
            }
        )
    for key in FRAMEWORK_ONLY_META_KEYS:
        result.pop(key, None)
    meta = editor_doc.get("framework_meta") or {}
    # Absent from the payload means the editor does not model it: keep the
    # document's value (already carried over with the other unknown keys).
    if "subject_question_urn" in meta:
        subject = str(meta.get("subject_question_urn") or "").lower()
        # A question added in this session carries the editor's URN until saved.
        subject = urn_map.get(subject, subject)
        if subject:
            result["subject_question_urn"] = subject
        else:
            result.pop("subject_question_urn", None)
    if "on_accept" in meta:
        if meta.get("on_accept"):
            result["on_accept"] = meta["on_accept"]
        else:
            result.pop("on_accept", None)
    # Rules and conditions written before the first save name the editor's ids.
    maps = node_id_maps(urn_map)
    if any(maps):
        for rule in result.get("outcomes_definition") or []:
            if isinstance(rule, dict) and rule.get("expression"):
                rule["expression"] = rebase_expression(rule["expression"], maps)
        for page in pages:
            if page.get("visibility_expression"):
                page["visibility_expression"] = rebase_expression(
                    page["visibility_expression"], maps
                )
    result["pages"] = pages
    return result
