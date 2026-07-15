"""
Library builder helpers.

The builder treats a work-in-progress library as a document (core.LibraryDraft)
that serializes to the same library YAML the tools/ Excel converter produces.
Publishing routes that YAML through the existing StoredLibrary/loader path —
the builder never writes live referential objects itself.

This module holds the document-level operations:

- URN minting from the draft identity (packager, ref_id)
- identity rebasing of a whole document (rename while unpublished)
- selective extraction ("clone") of objects out of an existing library's
  content, with per-reference policies (strip / pull / reference)
- merging extracted objects into a draft document
- advisory identity-conflict checks against the existing library corpus
- reference/dependency integrity checks used by the validate action
"""

import copy
import re

import structlog

logger = structlog.get_logger(__name__)

# Canonical (plural, list-valued) spellings for the objects container.
# The loader accepts the deprecated singular spellings; the builder normalizes
# to the canonical ones at ingestion so editing code handles a single shape.
CANONICAL_OBJECT_FIELDS = {
    "framework": "frameworks",
    "risk_matrix": "risk_matrices",
    "requirement_mapping_set": "requirement_mapping_sets",
}
LIST_OBJECT_FIELDS = [
    "frameworks",
    "threats",
    "reference_controls",
    "risk_matrices",
    "requirement_mapping_sets",
    "metric_definitions",
]
# URN type tokens per object field. "function" is the legacy spelling of
# "reference_control": recognized on input, never minted.
URN_TYPE_TOKENS = {
    "frameworks": "framework",
    "threats": "threat",
    "reference_controls": "reference_control",
    "risk_matrices": "matrix",
    "requirement_mapping_sets": "req_mapping_set",
    "metric_definitions": "metric",
}
# Kinds the builder allows at most ONE of per library (enforced at the API
# layer; adopted legacy documents may carry more): a single selected object
# of these kinds gets the bare family URN. Mapping sets are deliberately NOT
# here — a library legitimately holds several (e.g. both directions of a
# crosswalk), so they always mint with their own leaf.
SINGLETON_OBJECT_FIELDS = {"frameworks", "risk_matrices"}

POLICY_STRIP = "strip"
POLICY_PULL = "pull"
POLICY_REFERENCE = "reference"
REFERENCE_POLICIES = (POLICY_STRIP, POLICY_PULL, POLICY_REFERENCE)

# Characters allowed in the last URN segment (see core.models.URN_REGEX),
# minus ":" which is the segment separator.
_LEAF_FORBIDDEN = re.compile(r"[^0-9a-z\[\]\(\)\-\._]+")


class BuilderError(ValueError):
    """Document-level operation error, safe to surface to the client."""


def urn_safe_leaf(value: str) -> str:
    """Turn a ref_id into a string usable as the last URN segment."""
    leaf = _LEAF_FORBIDDEN.sub("-", str(value).lower().strip()).strip("-")
    return leaf


def library_urn(packager: str, ref_id: str) -> str:
    return f"urn:{packager}:risk:library:{ref_id}"


def object_urn_base(packager: str, ref_id: str, field: str) -> str:
    return f"urn:{packager}:risk:{URN_TYPE_TOKENS[field]}:{ref_id}"


def leaf_object_base(library_urn: str, field: str) -> str:
    """Derive the URN base for a library's objects of a given field from the
    library URN itself. Works for minted identities (…:risk:library:{ref})
    and adopted legacy identities (arbitrary type token, dotted ref) alike:
    only the type token is swapped.
    """
    match = re.match(
        r"^urn:([a-z0-9_-]+):([a-z0-9_-]+):([a-z0-9_-]+):(.+)$", library_urn.lower()
    )
    if not match:
        raise BuilderError(f"Cannot derive object URNs from {library_urn}")
    packager, domain, _, ref = match.groups()
    return f"urn:{packager}:{domain}:{URN_TYPE_TOKENS[field]}:{ref}"


def normalize_objects(objects: dict) -> dict:
    """Return a copy of an objects container with canonical field spellings.

    Deprecated singular fields are renamed to their plural form and their
    value wrapped into a list when needed. Unknown fields are kept verbatim
    so no construct the YAML schema can express is dropped.
    """
    normalized = {}
    for field, value in (objects or {}).items():
        canonical = CANONICAL_OBJECT_FIELDS.get(field, field)
        if canonical in LIST_OBJECT_FIELDS and isinstance(value, dict):
            value = [value]
        if canonical in normalized and isinstance(normalized[canonical], list):
            # e.g. both "framework" and "frameworks" present
            normalized[canonical] = normalized[canonical] + list(value)
        else:
            normalized[canonical] = value
    return normalized


def check_document_shape(objects: dict) -> list:
    """Structural validation of a (normalized) objects container.

    Shape only — completeness stays a validate/publish concern: a field may
    be absent or empty, but when present it must have the right type. This
    runs at every door content can enter through (draft save, adopt, import
    source), so everything past the boundary can assume well-formed
    structure instead of defending against arbitrary JSON. Unknown fields
    are ignored (round-trip tolerance).
    """
    errors = []
    seen_urns: dict = {}

    def type_error(path, expected):
        errors.append(f"{path}: must be {expected}")

    def note_urn(value, path):
        """Every identity URN in the document must be unique — two objects
        sharing a URN silently merge at load (update_or_create last-wins) or
        crash on the unique constraint. URNs embed a type token, so cross-
        kind collisions never happen naturally; a repeat is a real defect."""
        if not isinstance(value, str) or not value:
            return
        key = value.lower()
        if key in seen_urns:
            errors.append(
                f"{path}: duplicate URN {value} (already at {seen_urns[key]})"
            )
        else:
            seen_urns[key] = path

    def check_str_list(value, path):
        if not isinstance(value, list):
            type_error(path, "a list of URN strings")
            return
        for index, item in enumerate(value):
            if not isinstance(item, str):
                type_error(f"{path}[{index}]", "a URN string")

    def check_dict_list(value, path):
        """Report non-conforming entries; yield the well-formed ones."""
        if not isinstance(value, list):
            type_error(path, "a list of objects")
            return []
        entries = []
        for index, item in enumerate(value):
            if isinstance(item, dict):
                entries.append((index, item))
            else:
                type_error(f"{path}[{index}]", "an object")
        return entries

    top_level = {}
    for field in LIST_OBJECT_FIELDS:
        if field not in objects:
            continue
        top_level[field] = check_dict_list(objects[field], f"content.{field}")
        for index, obj in top_level[field]:
            urn = obj.get("urn")
            if urn is not None and not isinstance(urn, str):
                type_error(f"content.{field}[{index}].urn", "a string")
            else:
                note_urn(urn, f"content.{field}[{index}]")

    preset = objects.get("preset")
    if preset is not None:
        if not isinstance(preset, dict):
            type_error("content.preset", "an object")
        else:
            journey = preset.get("journey")
            if journey is not None and not isinstance(journey, dict):
                type_error("content.preset.journey", "an object")

    for index, framework in top_level.get("frameworks", []):
        path = f"content.frameworks[{index}]"
        nodes = framework.get("requirement_nodes")
        if nodes is None:
            continue
        for node_index, node in check_dict_list(nodes, f"{path}.requirement_nodes"):
            node_path = f"{path}.requirement_nodes[{node_index}]"
            for str_field in ("urn", "parent_urn"):
                value = node.get(str_field)
                if value is not None and not isinstance(value, str):
                    type_error(f"{node_path}.{str_field}", "a string")
            note_urn(node.get("urn"), node_path)
            for ref_field in ("threats", "reference_controls"):
                refs = node.get(ref_field)
                if refs is not None:
                    check_str_list(refs, f"{node_path}.{ref_field}")
            questions = node.get("questions")
            if questions is None:
                continue
            if not isinstance(questions, dict):
                type_error(f"{node_path}.questions", "an object keyed by URN")
                continue
            for q_urn, question in questions.items():
                q_path = f"{node_path}.questions[{q_urn}]"
                note_urn(q_urn, q_path)
                if not isinstance(question, dict):
                    type_error(q_path, "an object")
                    continue
                choices = question.get("choices")
                if choices is not None:
                    for choice_index, choice in check_dict_list(
                        choices, f"{q_path}.choices"
                    ):
                        choice_urn = choice.get("urn")
                        if choice_urn is not None and not isinstance(choice_urn, str):
                            type_error(
                                f"{q_path}.choices[{choice_index}].urn", "a string"
                            )
                        else:
                            note_urn(choice_urn, f"{q_path}.choices[{choice_index}]")

    for index, mapping_set in top_level.get("requirement_mapping_sets", []):
        path = f"content.requirement_mapping_sets[{index}]"
        for ref_field in ("source_framework_urn", "target_framework_urn"):
            value = mapping_set.get(ref_field)
            if value is not None and not isinstance(value, str):
                type_error(f"{path}.{ref_field}", "a string")
        mappings = mapping_set.get("requirement_mappings")
        if mappings is not None:
            check_dict_list(mappings, f"{path}.requirement_mappings")

    return errors


def index_objects(objects: dict) -> dict:
    """Map every top-level object URN (lowercased) to its (field, object).

    Tolerates malformed containers (non-list fields, non-dict entries):
    draft content is shape-checked at its doors, but this also runs over
    stored-library content, which is not.
    """
    index = {}
    for field in LIST_OBJECT_FIELDS:
        value = objects.get(field)
        if not isinstance(value, list):
            continue
        for obj in value:
            if not isinstance(obj, dict):
                continue
            urn = str(obj.get("urn", "")).lower()
            if urn:
                index[urn] = (field, obj)
    return index


def _dedup(leaf: str, taken: set) -> str:
    candidate = leaf
    suffix = 2
    while candidate in taken:
        candidate = f"{leaf}-{suffix}"
        suffix += 1
    taken.add(candidate)
    return candidate


def _object_leaf(obj: dict) -> str:
    leaf = urn_safe_leaf(obj.get("ref_id") or "")
    if not leaf:
        old_urn = str(obj.get("urn", ""))
        leaf = urn_safe_leaf(old_urn.rsplit(":", 1)[-1]) if old_urn else ""
    return leaf or "object"


def build_urn_map(
    objects: dict, selected_urns: set, packager: str, ref_id: str
) -> dict:
    """Compute old URN → new URN for the selected top-level objects.

    Frameworks additionally get one entry per requirement node, so that
    parent_urn links and question/choice URNs (which extend node URNs)
    follow through prefix substitution.
    """
    urn_map = {}
    for field in LIST_OBJECT_FIELDS:
        candidates = [
            obj
            for obj in objects.get(field) or []
            if str(obj.get("urn", "")).lower() in selected_urns
        ]
        if not candidates:
            continue
        base = object_urn_base(packager, ref_id, field)
        bare_base = field in SINGLETON_OBJECT_FIELDS and len(candidates) == 1
        taken_leaves = set()
        for obj in candidates:
            old_urn = str(obj["urn"]).lower()
            if bare_base:
                new_urn = base
            else:
                new_urn = f"{base}:{_dedup(_object_leaf(obj), taken_leaves)}"
            urn_map[old_urn] = new_urn
            if field == "frameworks":
                node_base = new_urn.replace(":framework:", ":req_node:", 1)
                _map_requirement_nodes(obj, old_urn, node_base, urn_map)
    return urn_map


def _map_requirement_nodes(
    framework: dict, old_framework_urn: str, node_base: str, urn_map: dict
) -> None:
    # Conventional node namespace of the source framework: keeping each
    # node's suffix relative to it preserves hierarchical ref schemes.
    old_node_base = old_framework_urn.replace(":framework:", ":req_node:", 1) + ":"
    taken_leaves = set()
    for node in framework.get("requirement_nodes") or []:
        old_urn = str(node.get("urn", "")).lower()
        if not old_urn:
            continue
        if old_urn.startswith(old_node_base):
            leaf = old_urn[len(old_node_base) :]
        else:
            leaf = _object_leaf(node)
        urn_map[old_urn] = f"{node_base}:{_dedup(leaf, taken_leaves)}"


def rebase_string(value: str, urn_map: dict) -> str:
    """Rewrite a string if it is a mapped URN or extends one (urn + ':...')."""
    lowered = value.lower()
    if lowered in urn_map:
        return urn_map[lowered]
    # Question/choice URNs extend a node URN: walk prefixes at ':' boundaries.
    prefix = lowered
    while ":" in prefix:
        prefix = prefix.rsplit(":", 1)[0]
        if prefix in urn_map:
            return urn_map[prefix] + lowered[len(prefix) :]
    return value


def rebase_tree(value, urn_map: dict):
    """Recursively rewrite mapped URNs in strings, list items and dict keys."""
    if isinstance(value, str):
        return rebase_string(value, urn_map)
    if isinstance(value, list):
        return [rebase_tree(item, urn_map) for item in value]
    if isinstance(value, dict):
        return {
            rebase_string(key, urn_map) if isinstance(key, str) else key: rebase_tree(
                item, urn_map
            )
            for key, item in value.items()
        }
    return value


def rebase_document(objects: dict, packager: str, ref_id: str) -> dict:
    """Rebase a whole draft document onto a new identity (draft rename).

    Every object is 'selected': the URN family is regenerated across the
    document; URNs pointing outside the document (dependencies) are kept.
    """
    normalized = normalize_objects(objects)
    selected = set(index_objects(normalized).keys())
    urn_map = build_urn_map(normalized, selected, packager, ref_id)
    return rebase_tree(copy.deepcopy(normalized), urn_map)


def _iter_framework_reference_lists(framework: dict):
    for node in framework.get("requirement_nodes") or []:
        for ref_field in ("threats", "reference_controls"):
            refs = node.get(ref_field)
            if refs:
                yield node, ref_field, refs


def extract_objects(
    *,
    source_content: dict,
    source_library_urn,
    source_dependencies,
    target_packager: str,
    target_ref_id: str,
    selected_types=None,
    selected_urns=None,
    default_policy: str = POLICY_STRIP,
    per_urn_policies=None,
    resolve_owner=None,
) -> dict:
    """Selective extraction: copy objects by value out of a library's content,
    rebased onto the target identity. Document → document; never touches live
    objects.

    Only frameworks (and mapping sets) carry references. A reference pointing
    at a source object *outside* the selection is resolved per policy:
    - strip: drop the link
    - pull: extract the referenced object too (closure)
    - reference: keep the source URN and add a dependency on the source library
    References already pointing outside the source library are kept and their
    owning libraries recorded as dependencies.

    Returns {"objects", "dependencies", "urn_map", "report"}.
    """
    if default_policy not in REFERENCE_POLICIES:
        raise BuilderError(f"Unknown reference policy: {default_policy}")
    # Request payload: a list or scalar would crash on .items() (500);
    # BuilderError is what the views translate into a 400.
    if per_urn_policies is not None and not isinstance(per_urn_policies, dict):
        raise BuilderError("Reference policies must be an object keyed by URN")
    per_urn_policies = {
        str(urn).lower(): policy for urn, policy in (per_urn_policies or {}).items()
    }
    for urn, policy in per_urn_policies.items():
        if policy not in REFERENCE_POLICIES:
            raise BuilderError(f"Unknown reference policy for {urn}: {policy}")

    objects = normalize_objects(copy.deepcopy(source_content))
    index = index_objects(objects)

    # Resolve the selection to a set of top-level object URNs (+ preset flag).
    selected_types = list(selected_types or [])
    include_preset = False
    selection = set()
    if not selected_types and not selected_urns:
        selection = set(index.keys())
        include_preset = "preset" in objects
    else:
        for field in selected_types:
            canonical = CANONICAL_OBJECT_FIELDS.get(field, field)
            if canonical == "preset":
                include_preset = "preset" in objects
                continue
            if canonical not in LIST_OBJECT_FIELDS:
                raise BuilderError(f"Unknown object type: {field}")
            selection.update(urn for urn, (f, _) in index.items() if f == canonical)
        for urn in selected_urns or []:
            lowered = str(urn).lower()
            if lowered not in index:
                raise BuilderError(f"Object not found in source library: {urn}")
            selection.add(lowered)

    report = {
        "pulled": [],
        "stripped": [],
        "referenced": [],
        "external": [],
        "unresolved": [],
    }

    def policy_for(ref: str) -> str:
        return per_urn_policies.get(ref, default_policy)

    # Closure pass: pull-in referenced source objects until stable.
    worklist = True
    while worklist:
        worklist = False
        for urn in list(selection):
            field, obj = index[urn]
            internal_refs = []
            if field == "frameworks":
                internal_refs = [
                    ref
                    for _, _, refs in _iter_framework_reference_lists(obj)
                    for ref in refs
                ]
            elif field == "requirement_mapping_sets":
                internal_refs = [
                    obj.get("source_framework_urn"),
                    obj.get("target_framework_urn"),
                ]
            for ref in internal_refs:
                lowered = str(ref or "").lower()
                if (
                    lowered in index
                    and lowered not in selection
                    and policy_for(lowered) == POLICY_PULL
                ):
                    selection.add(lowered)
                    report["pulled"].append(lowered)
                    worklist = True

    dependencies = set()

    def note_external(ref: str) -> None:
        """Record the dependency covering a reference kept by URN."""
        owner = resolve_owner(ref) if resolve_owner else None
        if owner:
            dependencies.add(owner)
            report["external"].append({"urn": ref, "library": owner})
        else:
            report["unresolved"].append(ref)
            dependencies.update(source_dependencies or [])

    # Reference resolution pass on the objects being extracted.
    for urn in selection:
        field, obj = index[urn]
        if field == "frameworks":
            for node, ref_field, refs in _iter_framework_reference_lists(obj):
                kept = []
                for ref in refs:
                    lowered = str(ref).lower()
                    if lowered in selection:
                        kept.append(lowered)
                    elif lowered in index:  # internal to source, not selected
                        policy = policy_for(lowered)
                        if policy == POLICY_STRIP:
                            report["stripped"].append(
                                {
                                    "node": str(node.get("urn", "")).lower(),
                                    "ref": lowered,
                                }
                            )
                        else:  # reference (pull already handled in closure)
                            if not source_library_urn:
                                raise BuilderError(
                                    "Cannot keep a reference to the source library: "
                                    "its URN is unknown"
                                )
                            kept.append(lowered)
                            dependencies.add(source_library_urn)
                            report["referenced"].append(lowered)
                    else:  # already external to the source library
                        kept.append(lowered)
                        note_external(lowered)
                node[ref_field] = kept
        elif field == "requirement_mapping_sets":
            for ref_field in ("source_framework_urn", "target_framework_urn"):
                ref = str(obj.get(ref_field) or "").lower()
                if not ref or ref in selection:
                    continue
                if ref in index:
                    # A mapping set cannot exist without its frameworks:
                    # strip is not applicable, keep the reference instead.
                    if not source_library_urn:
                        raise BuilderError(
                            "Cannot keep a reference to the source library: "
                            "its URN is unknown"
                        )
                    dependencies.add(source_library_urn)
                    report["referenced"].append(ref)
                else:
                    note_external(ref)

    urn_map = build_urn_map(objects, selection, target_packager, target_ref_id)

    extracted = {}
    for field in LIST_OBJECT_FIELDS:
        picked = [
            obj
            for obj in objects.get(field) or []
            if str(obj.get("urn", "")).lower() in selection
        ]
        if picked:
            extracted[field] = rebase_tree(picked, urn_map)
    if include_preset:
        extracted["preset"] = copy.deepcopy(objects["preset"])
        # Presets scaffold other libraries' objects by URN: carry the source
        # dependency list rather than deep-inspecting the preset document.
        dependencies.update(source_dependencies or [])

    dependencies.discard(library_urn(target_packager, target_ref_id))
    return {
        "objects": extracted,
        "dependencies": sorted(dependencies),
        "urn_map": urn_map,
        "report": report,
    }


def merge_objects(content: dict, new_objects: dict, overwrite: bool = False) -> dict:
    """Merge extracted objects into a draft document, keyed by URN.

    Raises BuilderError listing collisions unless overwrite is set, in which
    case colliding objects are replaced.
    """
    merged = normalize_objects(copy.deepcopy(content))
    collisions = []
    for field, incoming in new_objects.items():
        if field == "preset":
            if merged.get("preset") and not overwrite:
                collisions.append("preset")
            else:
                merged["preset"] = incoming
            continue
        existing = merged.setdefault(field, [])
        by_urn = {
            str(obj.get("urn", "")).lower(): pos for pos, obj in enumerate(existing)
        }
        for obj in incoming:
            urn = str(obj.get("urn", "")).lower()
            if urn in by_urn:
                if overwrite:
                    existing[by_urn[urn]] = obj
                else:
                    collisions.append(urn)
            else:
                by_urn[urn] = len(existing)
                existing.append(obj)
    if collisions:
        raise BuilderError(
            "Objects already present in the draft: {}".format(", ".join(collisions))
        )
    return merged


def find_owning_library_urn(urn: str, user=None):
    """Best-effort resolution of the loaded library owning an object URN.

    When `user` is given, only objects the user may read resolve — we see
    what we are allowed to see, full stop. None means system context.
    """
    from core.models import (
        Framework,
        ReferenceControl,
        RequirementMappingSet,
        RequirementNode,
        RiskMatrix,
        Threat,
    )
    from iam.models import RoleAssignment
    from metrology.models import MetricDefinition

    def readable(model, obj) -> bool:
        return user is None or RoleAssignment.is_object_readable(user, model, obj.id)

    lowered = str(urn).lower()
    for model in (Threat, ReferenceControl, Framework, RiskMatrix, MetricDefinition):
        obj = (
            model.objects.filter(urn=lowered, library__isnull=False)
            .select_related("library")
            .first()
        )
        if obj:
            return obj.library.urn if readable(model, obj) else None
    node = (
        RequirementNode.objects.filter(urn=lowered)
        .select_related("framework__library")
        .first()
    )
    if node and node.framework and node.framework.library:
        return node.framework.library.urn if readable(RequirementNode, node) else None
    mapping_set = (
        RequirementMappingSet.objects.filter(urn=lowered)
        .select_related("library")
        .first()
    )
    if mapping_set and mapping_set.library:
        return (
            mapping_set.library.urn
            if readable(RequirementMappingSet, mapping_set)
            else None
        )
    return None


def find_stored_owner_urn(
    urn: str, *, index_cache: dict | None = None, accessible_ids=None
):
    """Best-effort resolution of the *stored* library owning an object URN.

    Complements find_owning_library_urn for libraries that are stored but
    not loaded: inverts the URN-family convention (the library URN is the
    object URN with its type token swapped to `library`, minus trailing
    leaf segments) and verifies membership in the candidate's content.

    `index_cache` maps candidate library URNs to their content's URN set
    (None when no such stored library exists). Callers resolving many
    references pass one shared dict so each candidate library's content is
    fetched and indexed once, not once per reference. The cache embeds the
    visibility scope — never share it across users.

    `accessible_ids` restricts resolution to those stored-library ids
    (reading with the requesting user's eyes — an unreadable library is
    indistinguishable from a missing one); None means system context.
    """
    from core.models import StoredLibrary

    lowered = str(urn).lower()
    match = re.match(r"^urn:([a-z0-9_-]+):([a-z0-9_-]+):[a-z0-9_-]+:(.+)$", lowered)
    if not match:
        return None
    packager, domain, tail = match.groups()
    segments = tail.split(":")
    # Most specific candidate first: leaf objects carry extra segments after
    # the library ref (e.g. …:reference_control:doc-pol:pol.educ → doc-pol).
    candidates = [
        f"urn:{packager}:{domain}:library:{':'.join(segments[:i])}"
        for i in range(len(segments), 0, -1)
    ]
    if index_cache is None:
        index_cache = {}
    unknown = [candidate for candidate in candidates if candidate not in index_cache]
    if unknown:
        queryset = StoredLibrary.objects.filter(urn__in=unknown)
        if accessible_ids is not None:
            queryset = queryset.filter(id__in=accessible_ids)
        rows: dict = {}
        for stored in queryset:
            current = rows.get(stored.urn)
            if current is None or stored.version > current.version:
                rows[stored.urn] = stored
        for candidate in unknown:
            stored = rows.get(candidate)
            index_cache[candidate] = (
                set(index_objects(normalize_objects(stored.content or {})).keys())
                if stored
                else None
            )
    for candidate in candidates:
        members = index_cache.get(candidate)
        if members and lowered in members:
            return candidate
    return None


def accessible_stored_library_ids(user):
    """The stored-library ids the user may read, or None for system context.

    Resolution helpers accept this as their visibility scope so corpus
    lookups made on behalf of a user request never see more than the user
    could read directly.
    """
    if user is None:
        return None
    from core.models import StoredLibrary
    from iam.models import Folder, RoleAssignment

    return set(
        RoleAssignment.get_accessible_object_ids(
            Folder.get_root_folder(), user, StoredLibrary
        )[0]
    )


def check_identity_conflicts(
    packager: str, ref_id: str, exclude_draft_id=None, user=None
) -> list:
    """Advisory check of a draft identity against the existing corpus.

    Library-level conflicts are checked against StoredLibrary (broader than
    loaded), LoadedLibrary and other drafts. Object-level conflicts are
    checked against the loaded referential tables. The hard gate remains the
    loader's own uniqueness checks at publish time.

    Scoped to `user` when given — conflicts with objects the user cannot
    read are omitted (we see what we are allowed to see, full stop); the
    publish-time gate still refuses colliding identities. None means system
    context.
    """
    from core.models import (
        Framework,
        LibraryDraft,
        LoadedLibrary,
        ReferenceControl,
        RequirementMappingSet,
        RiskMatrix,
        StoredLibrary,
        Threat,
    )
    from django.db.models import Q
    from iam.models import Folder, RoleAssignment
    from metrology.models import MetricDefinition

    def scope(queryset, model):
        if user is None:
            return queryset
        ids = RoleAssignment.get_accessible_object_ids(
            Folder.get_root_folder(), user, model
        )[0]
        return queryset.filter(id__in=ids)

    conflicts = []
    lib_urn = library_urn(packager, ref_id)
    for model, kind in (
        (StoredLibrary, "stored_library"),
        (LoadedLibrary, "loaded_library"),
    ):
        for hit in scope(model.objects.filter(urn=lib_urn), model):
            conflicts.append(
                {
                    "kind": kind,
                    "urn": hit.urn,
                    "name": hit.name,
                    "version": hit.version,
                }
            )
    drafts = scope(
        LibraryDraft.objects.filter(
            Q(urn=lib_urn) | Q(urn__isnull=True, packager=packager, ref_id=ref_id)
        ),
        LibraryDraft,
    )
    if exclude_draft_id:
        drafts = drafts.exclude(id=exclude_draft_id)
    for draft in drafts:
        conflicts.append(
            {
                "kind": "library_draft",
                "urn": draft.effective_urn,
                "name": draft.name,
                "version": draft.version,
            }
        )

    object_models = {
        "frameworks": Framework,
        "threats": Threat,
        "reference_controls": ReferenceControl,
        "risk_matrices": RiskMatrix,
        "requirement_mapping_sets": RequirementMappingSet,
        "metric_definitions": MetricDefinition,
    }
    for field, model in object_models.items():
        base = object_urn_base(packager, ref_id, field)
        hits = scope(
            model.objects.filter(Q(urn=base) | Q(urn__startswith=base + ":")), model
        ).select_related("library")[:10]
        for hit in hits:
            conflicts.append(
                {
                    "kind": "loaded_object",
                    "urn": hit.urn,
                    "name": hit.name,
                    "library": hit.library.urn if hit.library else None,
                }
            )
    return conflicts


# DB varchar limits (core.models). SQLite ignores them silently, so an
# oversized value only crashes at publish on Postgres — validate must reject
# it up front so the failure is the same everywhere.
_MAX_LENGTHS = {"name": 200, "ref_id": 100, "urn": 255}


def _check_field_lengths(objects: dict) -> list:
    errors = []

    def check(obj, path):
        if not isinstance(obj, dict):
            return
        for field, limit in _MAX_LENGTHS.items():
            value = obj.get(field)
            if isinstance(value, str) and len(value) > limit:
                errors.append(
                    f"{path}.{field} is {len(value)} characters (max {limit})"
                )

    for field in LIST_OBJECT_FIELDS:
        for index, obj in enumerate(objects.get(field) or []):
            check(obj, f"content.{field}[{index}]")

    for fw_index, framework in enumerate(objects.get("frameworks") or []):
        if not isinstance(framework, dict):
            continue
        base = f"content.frameworks[{fw_index}]"
        for node_index, node in enumerate(framework.get("requirement_nodes") or []):
            if not isinstance(node, dict):
                continue
            node_path = f"{base}.requirement_nodes[{node_index}]"
            check(node, node_path)
            questions = node.get("questions")
            if isinstance(questions, dict):
                for q_urn, question in questions.items():
                    if len(str(q_urn)) > _MAX_LENGTHS["urn"]:
                        errors.append(
                            f"{node_path}.questions[{q_urn}]: URN is "
                            f"{len(str(q_urn))} characters (max {_MAX_LENGTHS['urn']})"
                        )
                    if isinstance(question, dict):
                        for choice in question.get("choices") or []:
                            check(choice, f"{node_path}.questions[{q_urn}].choice")
    return errors


def validate_draft_document(draft, *, user=None) -> dict:
    """Dry-run validation of a draft: loader field validation + reference
    integrity + advisory identity conflicts. Never writes anything.

    When `user` is given, corpus lookups (stored-library contents backing
    dependencies and reference resolution) are scoped to what that user may
    read; hidden libraries behave as missing and their references come back
    unresolved. None means system context (unscoped)."""
    from core.models import StoredLibrary
    from library.utils import LibraryImporter

    errors = []
    warnings = []

    library = draft.to_library_dict()
    # Fixed messages are i18n codes (safeTranslate on the frontend); dynamic
    # ones (paths, URNs) stay literal and display as-is.
    if not draft.name:
        errors.append("libraryNeedsName")
    if not draft.content:
        errors.append("libraryHoldsNoObjects")

    if draft.content:
        normalized = normalize_objects(draft.content)
        # Shape gate: the deeper checks (and the loader shim) assume a
        # well-formed structure; report structural garbage as errors
        # instead of crashing on it.
        if shape_errors := check_document_shape(normalized):
            return {"errors": errors + shape_errors, "warnings": warnings}
        errors.extend(_check_field_lengths(normalized))
        # Structural matrix validation (grid dims vs levels, cell indices).
        # RiskMatrixImporter.is_valid is a no-op and this validation runs
        # only for drafts, so a matrix reaching content via a raw PATCH
        # (bypassing the upsert-object door) is still checked before publish.
        from core.views import RiskMatrixViewSet

        for index, matrix in enumerate(normalized.get("risk_matrices") or []):
            if not isinstance(matrix, dict):
                continue
            definition = {
                key: matrix.get(key)
                for key in ("probability", "impact", "risk", "grid")
            }
            for matrix_error in RiskMatrixViewSet._validate_json_definition(definition):
                errors.append(f"content.risk_matrices[{index}]: {matrix_error}")
        shim = StoredLibrary(
            name=draft.name or "",
            urn=library["urn"],
            locale=draft.locale,
            version=draft.version,
            ref_id=draft.ref_id,
            content=normalized,
            dependencies=list(draft.dependencies or []),
        )
        try:
            error_msg = LibraryImporter(shim).init()
            if error_msg:
                errors.append(error_msg)
        except Exception:
            # The content already passed the shape gate, so this is an
            # internal validation bug: full detail to the log, a stable
            # code (localized by the panel's safeTranslate) to the client.
            logger.exception("Loader-level validation crashed", urn=library["urn"])
            errors.append("libraryValidationInternalError")

    errors.extend(_check_reference_integrity(draft, user=user))

    if not draft.identity_locked:
        for conflict in check_identity_conflicts(
            draft.packager, draft.ref_id, exclude_draft_id=draft.id, user=user
        ):
            warnings.append(
                "Identity conflict with {kind} {urn}".format(
                    kind=conflict["kind"], urn=conflict["urn"]
                )
            )
    return {"errors": errors, "warnings": warnings}


def _check_reference_integrity(draft, user=None) -> list:
    """Internal references must resolve within the draft; references leaving
    the draft must resolve to a known library, which must be a dependency.

    Corpus lookups are scoped to `user` when given (see
    validate_draft_document): a hidden stored library neither covers
    references nor gets named in error messages."""
    from core.models import StoredLibrary

    errors = []
    objects = normalize_objects(draft.content)
    internal = set(index_objects(objects).keys())
    node_urns = set()
    for framework in objects.get("frameworks") or []:
        for node in framework.get("requirement_nodes") or []:
            node_urns.add(str(node.get("urn", "")).lower())
    internal |= node_urns

    declared_dependencies = {str(dep).lower() for dep in draft.dependencies or []}
    own_urn = str(draft.effective_urn or "").lower()
    accessible = accessible_stored_library_ids(user)
    stored_index_cache: dict = {}  # shared across refs, see find_stored_owner_urn
    dependency_contents = None  # lazily-built URN index of dependency libraries

    def dependency_urns() -> set:
        nonlocal dependency_contents
        if dependency_contents is None:
            dependency_contents = set()
            queryset = StoredLibrary.objects.filter(urn__in=declared_dependencies)
            if accessible is not None:
                queryset = queryset.filter(id__in=accessible)
            for stored in queryset:
                dependency_contents.update(
                    index_objects(normalize_objects(stored.content or {})).keys()
                )
        return dependency_contents

    def check_ref(ref: str, where: str) -> None:
        lowered = str(ref).lower()
        if lowered in internal:
            return
        owner = find_owning_library_urn(lowered, user=user)
        if owner is None and lowered not in dependency_urns():
            # Not loaded, not covered by a declared dependency: a stored
            # library may still own it (better message than "unresolved").
            owner = find_stored_owner_urn(
                lowered, index_cache=stored_index_cache, accessible_ids=accessible
            )
            if owner is None:
                errors.append(f"{where}: unresolved reference {ref}")
                return
        if owner and owner.lower() == own_urn:
            # A stored/loaded copy of THIS library still holds the object:
            # the reference dangles in the draft — never suggest depending
            # on the library's own previous version.
            errors.append(f"{where}: unresolved reference {ref}")
            return
        if owner and owner.lower() not in declared_dependencies:
            errors.append(f"{where}: reference {ref} requires a dependency on {owner}")

    for framework in objects.get("frameworks") or []:
        fw_urn = str(framework.get("urn", "")).lower()
        # parent_urn must point inside THIS framework's tree: checking the
        # document-wide node set would let a multi-framework document (import
        # or adopt path) attach a node across frameworks and break the tree.
        framework_node_urns = {
            str(node.get("urn", "")).lower()
            for node in framework.get("requirement_nodes") or []
        }
        # A question's depends_on.question must reference a question that
        # exists in this framework, else the dependent question is invisible
        # forever in every audit (isQuestionVisible finds no answer for it).
        framework_question_urns = set()
        for node in framework.get("requirement_nodes") or []:
            questions = node.get("questions")
            if isinstance(questions, dict):
                framework_question_urns.update(
                    str(q_urn).lower() for q_urn in questions
                )
        for node in framework.get("requirement_nodes") or []:
            node_urn = str(node.get("urn", "")).lower()
            parent = node.get("parent_urn")
            if parent and str(parent).lower() not in framework_node_urns:
                errors.append(
                    f"{node_urn}: parent_urn {parent} is not a node of {fw_urn}"
                )
            for ref in node.get("threats") or []:
                check_ref(ref, node_urn)
            for ref in node.get("reference_controls") or []:
                check_ref(ref, node_urn)
            questions = node.get("questions")
            if isinstance(questions, dict):
                for q_urn, question in questions.items():
                    depends_on = (question or {}).get("depends_on")
                    target = (
                        depends_on.get("question")
                        if isinstance(depends_on, dict)
                        else None
                    )
                    if target and str(target).lower() not in framework_question_urns:
                        errors.append(
                            f"{q_urn}: depends_on references question {target} "
                            f"which is not in {fw_urn}"
                        )
    for mapping_set in objects.get("requirement_mapping_sets") or []:
        ms_urn = str(mapping_set.get("urn", "")).lower()
        for ref_field in ("source_framework_urn", "target_framework_urn"):
            ref = mapping_set.get(ref_field)
            if ref:
                check_ref(ref, ms_urn)
    return errors
