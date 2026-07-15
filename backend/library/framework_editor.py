"""
Bridge between the library-draft document and the visual framework editor.

The FrameworkBuilder frontend edits a flat "editor doc"
({framework_meta, nodes, questions, choices} — the historical editing_draft
schema). A library draft stores a framework as the library-YAML object
(requirement_nodes list, questions as a dict keyed by URN). This module
converts between the two so the visual editor can edit a framework *inside*
a LibraryDraft without any live Framework rows.

Rules:
- URNs of nodes/questions/choices that already exist in the document are
  kept verbatim (update-by-URN stability, incl. adopted legacy bases).
- New items get URNs minted under the framework's conventional node base
  (framework urn with :framework: replaced by :req_node:); whatever the
  editor minted client-side is remapped.
- Fields the editor does not model (min_score, max_score,
  scores_definition_ref, any unknown key) are preserved from the existing
  document object, matched by canonical URN.
- Node links to threats/reference controls are lists of full URNs, exactly
  as in the library YAML. A payload node that omits the key keeps the
  existing links (older clients don't model them); an empty list detaches.
"""

import copy

from library.builder import BuilderError, rebase_tree, urn_safe_leaf

# Node keys owned by the editor: everything else on an existing node is
# preserved verbatim across a save.
EDITOR_NODE_KEYS = {
    "urn",
    "ref_id",
    "name",
    "description",
    "annotation",
    "parent_urn",
    "assessable",
    "implementation_groups",
    "visibility_expression",
    "typical_evidence",
    "weight",
    "importance",
    "display_mode",
    "translations",
    "questions",
    "depth",
    "threats",
    "reference_controls",
}

# Framework-level keys owned by the editor (urn and ref_id are identity,
# never rewritten from the editor side).
EDITOR_FRAMEWORK_KEYS = {
    "name",
    "description",
    "annotation",
    "translations",
    "min_score",
    "max_score",
    "scores_definition",
    "implementation_groups_definition",
    "outcomes_definition",
    "field_visibility",
}

QUESTION_KEYS = {
    "type",
    "text",
    "annotation",
    "config",
    "depends_on",
    "weight",
    "translations",
    "choices",
}


def node_base_urn(framework_urn: str) -> str:
    framework_urn = framework_urn.lower()
    if ":framework:" in framework_urn:
        return framework_urn.replace(":framework:", ":req_node:", 1)
    return f"{framework_urn}:req_node"


def _normalize_question_type(raw_type) -> str:
    # Same normalization as the loader (_sync_questions_from_data).
    return "unique_choice" if raw_type == "single_choice" else (raw_type or "text")


def framework_to_editor_doc(framework: dict, *, locale: str = "en") -> dict:
    """Convert a library-YAML framework object into the editor doc shape."""
    urn = str(framework.get("urn", "")).lower()
    translations = framework.get("translations") or {}
    meta = {
        "name": framework.get("name") or "",
        "description": framework.get("description"),
        "annotation": framework.get("annotation"),
        "locale": locale,
        "translations": translations,
        "available_languages": sorted(translations.keys()),
        "min_score": framework.get("min_score", 0),
        "max_score": framework.get("max_score", 100),
        "scores_definition": framework.get("scores_definition"),
        "implementation_groups_definition": framework.get(
            "implementation_groups_definition"
        ),
        "outcomes_definition": framework.get("outcomes_definition"),
        "field_visibility": framework.get("field_visibility") or {},
        "urn_namespace": urn.split(":")[1] if urn.startswith("urn:") else "custom",
        "ref_id": framework.get("ref_id"),
    }

    nodes = []
    questions = []
    choices = []
    for order_id, node in enumerate(framework.get("requirement_nodes") or []):
        node_urn = str(node.get("urn", "")).lower()
        parent_urn = node.get("parent_urn")
        nodes.append(
            {
                "id": node_urn,
                "urn": node_urn,
                "ref_id": node.get("ref_id"),
                "name": node.get("name"),
                "description": node.get("description"),
                "annotation": node.get("annotation"),
                "parent_urn": str(parent_urn).lower() if parent_urn else None,
                "order_id": order_id,
                "assessable": bool(node.get("assessable")),
                "implementation_groups": node.get("implementation_groups"),
                "visibility_expression": node.get("visibility_expression"),
                "typical_evidence": node.get("typical_evidence"),
                "weight": node.get("weight", 1),
                "importance": node.get("importance"),
                "display_mode": node.get("display_mode", "default"),
                "folder_id": "",
                "translations": node.get("translations"),
                # Deduplicated (case variants collapse): the pill UI keys on
                # the URN, and adopted/raw-PATCHed content may carry repeats.
                "threats": list(
                    dict.fromkeys(str(ref).lower() for ref in node.get("threats") or [])
                ),
                "reference_controls": list(
                    dict.fromkeys(
                        str(ref).lower() for ref in node.get("reference_controls") or []
                    )
                ),
            }
        )
        questions_data = node.get("questions")
        if not isinstance(questions_data, dict):
            continue
        for q_order, (q_urn, q_data) in enumerate(questions_data.items()):
            q_urn = str(q_urn).lower()
            questions.append(
                {
                    "id": q_urn,
                    "urn": q_urn,
                    "ref_id": q_urn.rsplit(":", 1)[-1],
                    "text": q_data.get("text", ""),
                    "annotation": q_data.get("annotation"),
                    "type": _normalize_question_type(q_data.get("type")),
                    "config": q_data.get("config"),
                    "depends_on": q_data.get("depends_on"),
                    "order": q_order,
                    "weight": q_data.get("weight", 1),
                    "requirement_node_id": node_urn,
                    "folder_id": "",
                    "translations": q_data.get("translations"),
                }
            )
            for c_order, choice in enumerate(q_data.get("choices") or []):
                c_urn = choice.get("urn")
                c_urn = str(c_urn).lower() if c_urn else None
                choices.append(
                    {
                        "id": c_urn or f"{q_urn}:choice:{c_order + 1}",
                        "urn": c_urn,
                        "ref_id": c_urn.rsplit(":", 1)[-1] if c_urn else None,
                        "value": choice.get("value"),
                        "annotation": choice.get("annotation"),
                        "add_score": choice.get("add_score"),
                        "compute_result": choice.get("compute_result"),
                        "order": c_order,
                        "description": choice.get("description"),
                        "color": choice.get("color"),
                        "select_implementation_groups": choice.get(
                            "select_implementation_groups"
                        ),
                        "question_id": q_urn,
                        "folder_id": "",
                        "translations": choice.get("translations"),
                    }
                )

    return {
        "schema_version": 1,
        "framework_meta": meta,
        "nodes": nodes,
        "questions": questions,
        "choices": choices,
    }


def _dedup_leaf(leaf: str, taken: set) -> str:
    candidate = leaf
    suffix = 2
    while candidate in taken:
        candidate = f"{leaf}-{suffix}"
        suffix += 1
    taken.add(candidate)
    return candidate


def _clean(mapping: dict) -> dict:
    """Drop None values so the document (and its YAML export) stays lean."""
    return {key: value for key, value in mapping.items() if value is not None}


def editor_doc_to_framework_object(editor_doc: dict, *, existing: dict) -> dict:
    """Convert an editor doc back into the library-YAML framework object.

    `existing` is the framework object currently in the draft document; it
    provides the pinned framework URN, the set of known item URNs, and the
    fields the editor does not model.
    """
    framework_urn = str(existing.get("urn", "")).lower()
    if not framework_urn:
        raise BuilderError("The framework in the draft has no URN")
    base = node_base_urn(framework_urn)

    existing_nodes = {
        str(node.get("urn", "")).lower(): node
        for node in existing.get("requirement_nodes") or []
    }
    existing_question_urns = set()
    existing_choice_urns = set()
    for node in existing_nodes.values():
        questions_data = node.get("questions")
        if not isinstance(questions_data, dict):
            continue
        for q_urn, q_data in questions_data.items():
            existing_question_urns.add(str(q_urn).lower())
            for choice in q_data.get("choices") or []:
                if choice.get("urn"):
                    existing_choice_urns.add(str(choice["urn"]).lower())

    doc_nodes = editor_doc.get("nodes") or []
    doc_questions = editor_doc.get("questions") or []
    doc_choices = editor_doc.get("choices") or []

    # --- Canonicalize node URNs -------------------------------------------
    # Existing URNs are kept verbatim (whatever their base — adopted legacy
    # libraries keep their scheme); anything else is (re)minted under the
    # framework's node base. The editor references nodes both by id and urn,
    # so the map is keyed on both.
    urn_map: dict = {}
    node_ids_to_urn: dict = {}
    taken_leaves = set()
    for node in doc_nodes:
        node_urn = str(node.get("urn") or "").lower()
        if node_urn and node_urn in existing_nodes:
            leaf = (
                node_urn[len(base) + 1 :] if node_urn.startswith(base + ":") else None
            )
            if leaf:
                taken_leaves.add(leaf)

    minted = []
    for index, node in enumerate(doc_nodes):
        node_id = str(node.get("id") or "").lower()
        node_urn = str(node.get("urn") or "").lower()
        if node_urn and node_urn in existing_nodes:
            canonical = node_urn
        else:
            leaf = (
                urn_safe_leaf(node.get("ref_id") or "")
                or urn_safe_leaf(node.get("name") or "")
                or f"node{index + 1}"
            )
            canonical = f"{base}:{_dedup_leaf(leaf, taken_leaves)}"
            if node_urn:
                urn_map[node_urn] = canonical
        if node_id:
            node_ids_to_urn[node_id] = canonical
        minted.append(canonical)

    def map_ref(value):
        if not value:
            return None
        lowered = str(value).lower()
        return node_ids_to_urn.get(lowered) or urn_map.get(lowered) or lowered

    # --- Questions & choices, grouped per node -----------------------------
    questions_by_node: dict = {}
    choices_by_question: dict = {}
    for choice in doc_choices:
        choices_by_question.setdefault(str(choice.get("question_id") or ""), []).append(
            choice
        )

    question_id_to_urn: dict = {}
    # URNs claimed by questions during this save, per node. Minting must
    # avoid both these and every URN existing anywhere in the document —
    # existing questions keep their URN verbatim (whatever their position),
    # and a deleted question's URN must not be revived for new content.
    claimed_questions: dict = {}
    for question in sorted(doc_questions, key=lambda q: q.get("order") or 0):
        node_key = str(question.get("requirement_node_id") or "").lower()
        node_urn = node_ids_to_urn.get(node_key) or urn_map.get(node_key) or node_key
        claimed = claimed_questions.setdefault(node_urn, set())
        q_urn = str(question.get("urn") or "").lower()
        if q_urn and q_urn in existing_question_urns and q_urn not in claimed:
            claimed.add(q_urn)
        else:
            leaf = urn_safe_leaf(question.get("ref_id") or "") or str(len(claimed) + 1)
            candidate = f"{node_urn}:question:{leaf}"
            suffix = 2
            while candidate in existing_question_urns or candidate in claimed:
                candidate = f"{node_urn}:question:{leaf}-{suffix}"
                suffix += 1
            old_q_urn = q_urn
            q_urn = candidate
            claimed.add(q_urn)
            if old_q_urn:
                urn_map[old_q_urn] = q_urn
        question_id_to_urn[str(question.get("id") or "").lower()] = q_urn

        # For existing questions the editor id IS the urn: only add the
        # urn-keyed bucket when it differs, or every choice appears twice.
        question_id = str(question.get("id") or "")
        raw = list(choices_by_question.get(question_id, []))
        question_urn_key = str(question.get("urn") or "")
        if question_urn_key and question_urn_key != question_id:
            raw += choices_by_question.get(question_urn_key, [])
        raw_choices = sorted(raw, key=lambda c: c.get("order") or 0)

        q_choices = []
        claimed_choices: set = set()
        next_index = 1
        seen_choice_ids = set()
        for choice in raw_choices:
            choice_key = id(choice)
            if choice_key in seen_choice_ids:
                continue
            seen_choice_ids.add(choice_key)
            c_urn = str(choice.get("urn") or "").lower()
            if c_urn and c_urn in existing_choice_urns and c_urn not in claimed_choices:
                claimed_choices.add(c_urn)
            else:
                old_c_urn = c_urn
                candidate = f"{q_urn}:choice:{next_index}"
                while candidate in existing_choice_urns or candidate in claimed_choices:
                    next_index += 1
                    candidate = f"{q_urn}:choice:{next_index}"
                c_urn = candidate
                claimed_choices.add(c_urn)
                next_index += 1
                if old_c_urn:
                    urn_map[old_c_urn] = c_urn
            q_choices.append(
                _clean(
                    {
                        "urn": c_urn,
                        "value": choice.get("value"),
                        "annotation": choice.get("annotation"),
                        "add_score": choice.get("add_score"),
                        "compute_result": choice.get("compute_result"),
                        "description": choice.get("description"),
                        "color": choice.get("color"),
                        "select_implementation_groups": choice.get(
                            "select_implementation_groups"
                        ),
                        "translations": choice.get("translations"),
                    }
                )
            )

        questions_by_node.setdefault(node_urn, {})[q_urn] = _clean(
            {
                "type": _normalize_question_type(question.get("type")),
                "text": question.get("text") or "",
                "annotation": question.get("annotation"),
                "config": question.get("config"),
                "depends_on": question.get("depends_on"),
                "weight": question.get("weight"),
                "translations": question.get("translations"),
                "choices": q_choices or None,
            }
        )

    # --- Rebuild the requirement_nodes list in editor order ----------------
    # The node list is a pre-order tree serialization (the sequence+depth
    # convention shared with the Excel pipeline): every parent_urn must
    # reference a node that appears EARLIER in the list. Documents violating
    # this — possible only through raw API payloads, never through the editor
    # UI — are rejected as malformed rather than silently reinterpreted.
    # Forward references being rejected also makes parent cycles impossible.
    known_node_urns = set(minted)
    requirement_nodes = []
    depths: dict = {}
    for index, node in enumerate(doc_nodes):
        canonical = minted[index]
        parent = map_ref(node.get("parent_urn"))
        if parent is not None:
            if parent not in known_node_urns:
                raise BuilderError(
                    f"Node {canonical} references unknown parent "
                    f"{node.get('parent_urn')}"
                )
            if parent not in depths:
                raise BuilderError(
                    f"Malformed node order: {canonical} appears before "
                    f"its parent {parent}"
                )
        depth = depths[parent] + 1 if parent else 1
        depths[canonical] = depth
        node_dict = _clean(
            {
                "urn": canonical,
                "assessable": bool(node.get("assessable")),
                "depth": depth,
                "ref_id": node.get("ref_id"),
                "name": node.get("name"),
                "description": node.get("description"),
                "annotation": node.get("annotation"),
                "parent_urn": parent,
                "typical_evidence": node.get("typical_evidence"),
                "implementation_groups": node.get("implementation_groups"),
                "visibility_expression": node.get("visibility_expression"),
                "importance": node.get("importance"),
                "translations": node.get("translations"),
            }
        )
        weight = node.get("weight")
        if weight is not None and weight != 1:
            node_dict["weight"] = weight
        display_mode = node.get("display_mode")
        if display_mode and display_mode != "default":
            node_dict["display_mode"] = display_mode
        node_questions = questions_by_node.get(canonical)
        if node_questions:
            node_dict["questions"] = node_questions
        previous = existing_nodes.get(canonical)
        # Threat / reference-control links: lists of full URNs, as in the
        # library YAML. Key absent (or null) → the payload does not model
        # links, keep the existing ones; empty list → deliberate detach-all.
        for ref_field in ("threats", "reference_controls"):
            refs = node.get(ref_field)
            if ref_field in node and refs is not None:
                if not isinstance(refs, list) or not all(
                    isinstance(ref, str) for ref in refs
                ):
                    raise BuilderError(
                        f"{canonical}: {ref_field} must be a list of URN strings"
                    )
                cleaned = []
                for ref in refs:
                    lowered = ref.strip().lower()
                    if lowered and lowered not in cleaned:
                        cleaned.append(lowered)
                if cleaned:
                    node_dict[ref_field] = cleaned
            elif previous and previous.get(ref_field):
                node_dict[ref_field] = copy.deepcopy(previous[ref_field])
        # Preserve what the editor does not model (min_score,
        # scores_definition_ref, …).
        if previous:
            for key, value in previous.items():
                if key not in EDITOR_NODE_KEYS and key not in node_dict:
                    node_dict[key] = copy.deepcopy(value)
        requirement_nodes.append(node_dict)

    # Remap dangling references the editor may carry inside question configs
    # (depends_on targets, etc.): editor-minted URNs and editor-local ids both
    # map to the canonical URNs.
    for editor_id, canonical in {**node_ids_to_urn, **question_id_to_urn}.items():
        if editor_id and editor_id != canonical:
            urn_map[editor_id] = canonical
    if urn_map:
        requirement_nodes = rebase_tree(requirement_nodes, urn_map)

    # --- Framework object ---------------------------------------------------
    meta = editor_doc.get("framework_meta") or {}
    framework = {
        key: copy.deepcopy(value)
        for key, value in existing.items()
        if key not in EDITOR_FRAMEWORK_KEYS and key != "requirement_nodes"
    }
    framework.update(
        _clean(
            {
                "name": meta.get("name"),
                "description": meta.get("description"),
                "annotation": meta.get("annotation"),
                "translations": meta.get("translations") or None,
                "min_score": meta.get("min_score"),
                "max_score": meta.get("max_score"),
                "scores_definition": meta.get("scores_definition"),
                "implementation_groups_definition": meta.get(
                    "implementation_groups_definition"
                ),
                "outcomes_definition": meta.get("outcomes_definition"),
                "field_visibility": meta.get("field_visibility") or None,
            }
        )
    )
    if meta.get("ref_id"):
        framework["ref_id"] = meta["ref_id"]
    framework["urn"] = framework_urn
    framework["requirement_nodes"] = requirement_nodes
    return framework
