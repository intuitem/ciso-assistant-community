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

from library.builder import BuilderError
from library.framework_editor import (
    editor_doc_to_framework_object,
    framework_to_editor_doc,
)

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
    for key in FRAMEWORK_ONLY_META_KEYS:
        doc["framework_meta"].pop(key, None)
    return doc


def editor_doc_to_quick_form_object(editor_doc: dict, *, existing: dict) -> dict:
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
    result = editor_doc_to_framework_object(
        editor_doc, existing=pseudo_existing, node_base=page_base_urn(form_urn)
    )
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
    result["pages"] = pages
    return result
