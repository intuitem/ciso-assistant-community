"""
Serialization of live referential rows into library-YAML objects.

The inverse of the loader, for one narrow purpose: adopting a library-less
live framework (built with the retired standalone editor) into a library
draft. The draft then owns the document; publishing goes through the
standard loader, which updates the SAME live rows in place (update-by-URN),
so audits and assessments keep pointing where they always did.

The old editor kept frameworks editable precisely by leaving their URN
NULL, so most of this population carries no URNs. mint_missing_urns
backfills them deterministically onto the live rows first — that is what
makes update-in-place possible at publish time.
"""

from library.builder import urn_safe_leaf

_IDENTITY_FORBIDDEN = "[^a-z0-9_-]+"


def _identity_token(value: str, fallback: str) -> str:
    import re

    token = re.sub(_IDENTITY_FORBIDDEN, "-", str(value or "").lower()).strip("-")
    return token or fallback


def _clean(mapping: dict) -> dict:
    return {key: value for key, value in mapping.items() if value is not None}


def framework_identity(framework) -> tuple:
    """(packager, ref) tokens for the framework's URN family.

    Prefers the existing URN; falls back to the legacy editor's namespace
    seed and the slugged name/ref_id — the same seeds the old client-side
    minting used, so previously published node URNs stay in-family.
    """
    import re

    if framework.urn:
        match = re.match(
            r"^urn:([a-z0-9_-]+):([a-z0-9_.-]+):framework:(.+)$",
            framework.urn.lower(),
        )
        if match:
            return match.group(1), match.group(3)
    namespace = _identity_token(
        getattr(framework, "urn_namespace", None) or "custom", "custom"
    )
    # A node URN minted by the old editor embeds the framework slug:
    # urn:{ns}:risk:req_node:{slug}:{ref}
    for node in framework.requirement_nodes.exclude(urn=None).exclude(urn=""):
        parts = str(node.urn).split(":")
        if len(parts) >= 6 and parts[3] == "req_node":
            return namespace, parts[4]
    ref = _identity_token(
        framework.ref_id or framework.name, f"framework-{str(framework.id)[:8]}"
    )
    return namespace, ref


def mint_missing_urns(framework) -> bool:
    """Backfill URNs on the framework and its nodes/questions/choices.

    Existing URNs are never touched. Returns True when anything was
    written. Minted URNs follow the standard family so a later publish
    updates these very rows.
    """
    from core.models import Question, QuestionChoice, RequirementNode

    packager, ref = framework_identity(framework)
    wrote = False

    def _normalize(row) -> bool:
        """Lowercase an existing URN in place so a later publish (which
        looks rows up by the lowercased document URN) matches this very
        row instead of creating a duplicate. Returns True when written."""
        if row.urn and row.urn != str(row.urn).lower():
            row.urn = str(row.urn).lower()
            row.save(update_fields=["urn"])
            return True
        return False

    if not framework.urn:
        candidate = f"urn:{packager}:risk:framework:{ref}"
        suffix = 2
        while (
            type(framework)
            .objects.filter(urn=candidate)
            .exclude(id=framework.id)
            .exists()
        ):
            candidate = f"urn:{packager}:risk:framework:{ref}-{suffix}"
            suffix += 1
        framework.urn = candidate
        framework.save(update_fields=["urn"])
        wrote = True
    elif _normalize(framework):
        wrote = True

    node_base = framework.urn.lower().replace(":framework:", ":req_node:", 1)
    nodes = list(RequirementNode.objects.filter(framework=framework))
    taken = {str(n.urn).lower() for n in nodes if n.urn}
    for index, node in enumerate(nodes):
        if node.urn:
            wrote = _normalize(node) or wrote
            continue
        leaf = (
            urn_safe_leaf(node.ref_id or "")
            or urn_safe_leaf(node.name or "")
            or f"node{index + 1}"
        )
        candidate = f"{node_base}:{leaf}"
        suffix = 2
        while (
            candidate in taken or RequirementNode.objects.filter(urn=candidate).exists()
        ):
            candidate = f"{node_base}:{leaf}-{suffix}"
            suffix += 1
        taken.add(candidate)
        node.urn = candidate
        node.save(update_fields=["urn"])
        wrote = True

    for node in nodes:
        questions = list(
            Question.objects.filter(requirement_node=node).order_by("order")
        )
        q_taken = {str(q.urn).lower() for q in questions if q.urn}
        for q_index, question in enumerate(questions):
            if question.urn:
                wrote = _normalize(question) or wrote
            else:
                candidate = f"{str(node.urn).lower()}:question:{q_index + 1}"
                suffix = 2
                while candidate in q_taken:
                    candidate = (
                        f"{str(node.urn).lower()}:question:{q_index + 1}-{suffix}"
                    )
                    suffix += 1
                q_taken.add(candidate)
                question.urn = candidate
                question.save(update_fields=["urn"])
                wrote = True
            choices = list(
                QuestionChoice.objects.filter(question=question).order_by("order")
            )
            c_taken = {str(c.urn).lower() for c in choices if c.urn}
            for c_index, choice in enumerate(choices):
                if choice.urn:
                    wrote = _normalize(choice) or wrote
                    continue
                candidate = f"{str(question.urn).lower()}:choice:{c_index + 1}"
                suffix = 2
                while candidate in c_taken:
                    candidate = (
                        f"{str(question.urn).lower()}:choice:{c_index + 1}-{suffix}"
                    )
                    suffix += 1
                c_taken.add(candidate)
                choice.urn = candidate
                choice.save(update_fields=["urn"])
                wrote = True
    return wrote


def live_framework_to_object(framework) -> dict:
    """Serialize a live framework tree into the library-YAML framework object.

    Requires URNs everywhere (run mint_missing_urns first). Nodes come out
    in pre-order (parents before children), matching the document invariant.
    """
    from core.models import Question, QuestionChoice, RequirementNode

    nodes = list(RequirementNode.objects.filter(framework=framework))
    children: dict = {}
    for node in nodes:
        parent = str(node.parent_urn).lower() if node.parent_urn else None
        children.setdefault(parent, []).append(node)
    for siblings in children.values():
        siblings.sort(key=lambda n: n.order_id if n.order_id is not None else 0)

    questions_by_node: dict = {}
    for question in Question.objects.filter(requirement_node__framework=framework):
        questions_by_node.setdefault(question.requirement_node_id, []).append(question)
    choices_by_question: dict = {}
    for choice in QuestionChoice.objects.filter(
        question__requirement_node__framework=framework
    ):
        choices_by_question.setdefault(choice.question_id, []).append(choice)

    def serialize_node(node, depth: int) -> dict:
        node_dict = _clean(
            {
                "urn": str(node.urn).lower(),
                "assessable": bool(node.assessable),
                "depth": depth,
                "parent_urn": str(node.parent_urn).lower() if node.parent_urn else None,
                "ref_id": node.ref_id,
                "name": node.name,
                "description": node.description,
                "annotation": node.annotation,
                "typical_evidence": node.typical_evidence,
                "implementation_groups": node.implementation_groups,
                "visibility_expression": node.visibility_expression,
                "translations": node.translations or None,
            }
        )
        if node.weight is not None and node.weight != 1:
            node_dict["weight"] = node.weight
        if node.importance and node.importance != "undefined":
            node_dict["importance"] = node.importance
        if node.display_mode and node.display_mode != "default":
            node_dict["display_mode"] = node.display_mode
        threats = sorted(node.threats.values_list("urn", flat=True))
        if threats:
            node_dict["threats"] = [str(urn).lower() for urn in threats if urn]
        controls = sorted(node.reference_controls.values_list("urn", flat=True))
        if controls:
            node_dict["reference_controls"] = [
                str(urn).lower() for urn in controls if urn
            ]
        questions = sorted(
            questions_by_node.get(node.id, []),
            key=lambda q: q.order if q.order is not None else 0,
        )
        if questions:
            questions_dict = {}
            for question in questions:
                q_choices = sorted(
                    choices_by_question.get(question.id, []),
                    key=lambda c: c.order if c.order is not None else 0,
                )
                questions_dict[str(question.urn).lower()] = _clean(
                    {
                        "type": question.type,
                        "text": question.text or "",
                        "annotation": question.annotation,
                        "config": question.config,
                        "depends_on": question.depends_on,
                        "weight": question.weight
                        if question.weight not in (None, 1)
                        else None,
                        "translations": question.translations or None,
                        "choices": [
                            _clean(
                                {
                                    "urn": str(choice.urn).lower(),
                                    "value": choice.value,
                                    "annotation": choice.annotation,
                                    "add_score": choice.add_score,
                                    "compute_result": choice.compute_result,
                                    "description": choice.description,
                                    "color": choice.color,
                                    "select_implementation_groups": choice.select_implementation_groups,
                                    "translations": choice.translations or None,
                                }
                            )
                            for choice in q_choices
                        ]
                        or None,
                    }
                )
            node_dict["questions"] = questions_dict
        return node_dict

    requirement_nodes = []
    serialized_urns: set = set()

    def walk(parent_urn, depth):
        for node in children.get(parent_urn, []):
            node_urn = str(node.urn).lower()
            if node_urn in serialized_urns:
                continue  # defends against a parent cycle
            serialized_urns.add(node_urn)
            node_dict = serialize_node(node, depth)
            requirement_nodes.append(node_dict)
            walk(node_urn, depth + 1)

    walk(None, 1)

    # Nodes whose parent_urn dangles (parent deleted via the API, legacy
    # data, or a cycle) are unreachable from the roots. Promote them to
    # roots rather than dropping them — dropping would make publish's node
    # prune delete live rows (and their assessments) the user never touched.
    node_urns = {str(node.urn).lower() for node in nodes}
    for parent_urn in sorted(
        key for key in children if key is not None and key not in node_urns
    ):
        for node in children[parent_urn]:
            node_urn = str(node.urn).lower()
            if node_urn in serialized_urns:
                continue
            serialized_urns.add(node_urn)
            node_dict = serialize_node(node, 1)
            node_dict.pop("parent_urn", None)  # the referenced parent is gone
            requirement_nodes.append(node_dict)
            walk(node_urn, 2)

    # Final sweep for any node still unserialized (a pure parent cycle whose
    # members all reference each other): break it by rooting them.
    for node in nodes:
        node_urn = str(node.urn).lower()
        if node_urn in serialized_urns:
            continue
        serialized_urns.add(node_urn)
        node_dict = serialize_node(node, 1)
        node_dict.pop("parent_urn", None)
        requirement_nodes.append(node_dict)
        walk(node_urn, 2)

    return _clean(
        {
            "urn": str(framework.urn).lower(),
            "ref_id": framework.ref_id or framework_identity(framework)[1],
            "name": framework.name,
            "description": framework.description,
            "annotation": framework.annotation,
            "min_score": framework.min_score,
            "max_score": framework.max_score,
            "scores_definition": framework.scores_definition,
            "implementation_groups_definition": framework.implementation_groups_definition,
            "outcomes_definition": framework.outcomes_definition,
            "field_visibility": framework.field_visibility or None,
            "translations": framework.translations or None,
            "requirement_nodes": requirement_nodes,
        }
    )
